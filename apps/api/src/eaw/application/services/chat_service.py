"""Enterprise grounded chat use cases."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from eaw.application.ports.llm import ChatMessage, LLMPort
from eaw.application.services.org_service import OrgService
from eaw.application.services.retrieval_service import RetrievalService
from eaw.core.config import Settings
from eaw.domain.common.enums import MembershipRole
from eaw.domain.common.errors import ForbiddenError, NotFoundError, ValidationAppError
from eaw.domain.tenancy.policies import can_read_knowledge, require_role
from eaw.infrastructure.db.models.conversation import (
    Conversation,
    Message,
    MessageCitation,
    MessageFeedback,
)
from eaw.infrastructure.db.models.knowledge import KnowledgeBase
from eaw.infrastructure.rag.prompts import build_system_prompt, suggest_followups

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        db: Session,
        org_service: OrgService,
        retrieval: RetrievalService,
        llm: LLMPort,
        settings: Settings,
    ) -> None:
        self.db = db
        self.org = org_service
        self.retrieval = retrieval
        self.llm = llm
        self.settings = settings

    def _kb(self, kb_id: UUID) -> KnowledgeBase:
        kb = self.db.get(KnowledgeBase, kb_id)
        if kb is None or kb.deleted_at is not None:
            raise NotFoundError("Knowledge base not found")
        return kb

    def _conv(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        conv = self.db.get(Conversation, conversation_id)
        if conv is None or conv.deleted_at is not None:
            raise NotFoundError("Conversation not found")
        if conv.user_id != user_id:
            raise ForbiddenError("You do not own this conversation")
        return conv

    def create_conversation(
        self, *, kb_id: UUID, user_id: UUID, title: Optional[str] = None
    ) -> Conversation:
        kb = self._kb(kb_id)
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="chat")

        conv = Conversation(
            organization_id=kb.organization_id,
            knowledge_base_id=kb.id,
            user_id=user_id,
            title=title or "New conversation",
            model=self.llm.model_name,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def list_conversations(
        self, *, kb_id: UUID, user_id: UUID
    ) -> list[Conversation]:
        kb = self._kb(kb_id)
        self.org.get_membership(kb.organization_id, user_id)
        return list(
            self.db.scalars(
                select(Conversation)
                .where(
                    Conversation.knowledge_base_id == kb_id,
                    Conversation.user_id == user_id,
                    Conversation.deleted_at.is_(None),
                )
                .order_by(Conversation.updated_at.desc())
            ).all()
        )

    def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        return self._conv(conversation_id, user_id)

    def rename_conversation(
        self, conversation_id: UUID, user_id: UUID, title: str
    ) -> Conversation:
        conv = self._conv(conversation_id, user_id)
        conv.title = title.strip()[:300]
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        conv = self._conv(conversation_id, user_id)
        conv.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    def list_messages(self, conversation_id: UUID, user_id: UUID) -> list[Message]:
        self._conv(conversation_id, user_id)
        return list(
            self.db.scalars(
                select(Message)
                .options(selectinload(Message.citations))
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            ).all()
        )

    def _history_messages(self, conversation_id: UUID) -> list[ChatMessage]:
        rows = list(
            self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(self.settings.chat_history_turns * 2)
            ).all()
        )
        rows.reverse()
        return [ChatMessage(role=m.role, content=m.content) for m in rows]

    def _maybe_update_memory(self, conv: Conversation) -> None:
        count = len(
            self.db.scalars(
                select(Message).where(Message.conversation_id == conv.id)
            ).all()
        )
        if count < self.settings.chat_memory_threshold_messages:
            return
        # Lightweight extractive memory: last N user questions
        users = [
            m.content
            for m in self.db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.role == "user",
                )
                .order_by(Message.created_at.desc())
                .limit(6)
            ).all()
        ]
        users.reverse()
        conv.memory_summary = "Topics discussed:\n- " + "\n- ".join(
            u[:200] for u in users
        )
        self.db.commit()

    def _build_rag(
        self, conv: Conversation, user_id: UUID, question: str
    ) -> tuple[list[dict], float, bool]:
        passages, confidence = self.retrieval.hybrid_retrieve(
            kb_id=conv.knowledge_base_id,
            user_id=user_id,
            query=question,
        )
        min_score = self.settings.rag_min_score
        insufficient = (not passages) or (confidence < min_score)
        # If top dense score is very low, refuse
        if passages and passages[0].score < min_score:
            insufficient = True

        passage_dicts: list[dict] = []
        if not insufficient:
            for p in passages:
                passage_dicts.append(
                    {
                        "rank": p.rank,
                        "title": p.title,
                        "content": p.content or p.hit.payload.get("content_preview") or "",
                        "score": p.score,
                        "document_id": p.hit.payload.get("document_id"),
                        "chunk_id": p.hit.payload.get("chunk_id") or p.hit.id,
                    }
                )
        return passage_dicts, confidence, insufficient

    def ask(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
        stream: bool = False,
    ) -> Iterator[dict[str, Any]] | dict[str, Any]:
        content = (content or "").strip()
        if not content:
            raise ValidationAppError("Message content is required")

        conv = self._conv(conversation_id, user_id)
        started = time.perf_counter()

        # Persist user message
        user_msg = Message(
            id=uuid4(),
            organization_id=conv.organization_id,
            conversation_id=conv.id,
            role="user",
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(user_msg)
        if conv.title in (None, "New conversation"):
            conv.title = content[:80]
        conv.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        passages, confidence, insufficient = self._build_rag(conv, user_id, content)
        prompt = build_system_prompt(
            passages=passages,
            memory_summary=conv.memory_summary,
            insufficient=insufficient,
        )
        history = self._history_messages(conv.id)
        messages = [ChatMessage(role="system", content=prompt.system), *history]

        assistant_id = uuid4()

        if stream:
            return self._stream_answer(
                conv=conv,
                assistant_id=assistant_id,
                messages=messages,
                passages=passages,
                confidence=confidence,
                insufficient=insufficient,
                question=content,
                started=started,
            )

        result = self.llm.complete(
            messages,
            temperature=self.settings.llm_temperature,
        )
        answer = result.content
        latency = int((time.perf_counter() - started) * 1000)
        asst = self._persist_assistant(
            conv=conv,
            assistant_id=assistant_id,
            content=answer,
            confidence=0.0 if insufficient else confidence,
            passages=passages if not insufficient else [],
            model=result.model,
            latency_ms=latency,
            token_count=result.output_tokens,
        )
        self._maybe_update_memory(conv)
        suggestions = suggest_followups(content, answer, not insufficient)
        return {
            "message": asst,
            "citations": asst.citations,
            "confidence": asst.confidence,
            "suggestions": suggestions,
            "insufficient_context": insufficient,
        }

    def _stream_answer(
        self,
        *,
        conv: Conversation,
        assistant_id: UUID,
        messages: list[ChatMessage],
        passages: list[dict],
        confidence: float,
        insufficient: bool,
        question: str,
        started: float,
    ) -> Iterator[dict[str, Any]]:
        yield {
            "event": "meta",
            "data": {
                "message_id": str(assistant_id),
                "model": self.llm.model_name,
                "insufficient_context": insufficient,
            },
        }

        if not insufficient:
            for p in passages:
                yield {
                    "event": "citation",
                    "data": {
                        "rank": p["rank"],
                        "title": p["title"],
                        "excerpt": (p["content"] or "")[:500],
                        "score": p["score"],
                        "document_id": p.get("document_id"),
                        "chunk_id": p.get("chunk_id"),
                    },
                }

        yield {
            "event": "confidence",
            "data": {"confidence": 0.0 if insufficient else confidence},
        }

        buf: list[str] = []
        try:
            for delta in self.llm.stream(
                messages, temperature=self.settings.llm_temperature
            ):
                buf.append(delta)
                yield {"event": "token", "data": {"delta": delta}}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stream failed")
            yield {"event": "error", "data": {"message": str(exc)}}
            answer = "".join(buf) or "An error occurred while generating the answer."
            self._persist_assistant(
                conv=conv,
                assistant_id=assistant_id,
                content=answer,
                confidence=0.0,
                passages=[],
                model=self.llm.model_name,
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=str(exc),
            )
            yield {"event": "done", "data": {"message_id": str(assistant_id)}}
            return

        answer = "".join(buf)
        latency = int((time.perf_counter() - started) * 1000)
        asst = self._persist_assistant(
            conv=conv,
            assistant_id=assistant_id,
            content=answer,
            confidence=0.0 if insufficient else confidence,
            passages=passages if not insufficient else [],
            model=self.llm.model_name,
            latency_ms=latency,
        )
        self._maybe_update_memory(conv)
        suggestions = suggest_followups(question, answer, not insufficient)
        yield {"event": "suggestions", "data": {"suggestions": suggestions}}
        yield {
            "event": "done",
            "data": {
                "message_id": str(asst.id),
                "confidence": asst.confidence,
                "latency_ms": latency,
            },
        }

    def _persist_assistant(
        self,
        *,
        conv: Conversation,
        assistant_id: UUID,
        content: str,
        confidence: float,
        passages: list[dict],
        model: str,
        latency_ms: int,
        token_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Message:
        msg = Message(
            id=assistant_id,
            organization_id=conv.organization_id,
            conversation_id=conv.id,
            role="assistant",
            content=content,
            confidence=confidence,
            token_count=token_count or (len(content) // 4),
            latency_ms=latency_ms,
            model=model,
            error=error,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(msg)
        self.db.flush()
        for p in passages:
            chunk_id = None
            doc_id = None
            try:
                if p.get("chunk_id"):
                    chunk_id = UUID(str(p["chunk_id"]))
            except Exception:  # noqa: BLE001
                chunk_id = None
            try:
                if p.get("document_id"):
                    doc_id = UUID(str(p["document_id"]))
            except Exception:  # noqa: BLE001
                doc_id = None
            self.db.add(
                MessageCitation(
                    organization_id=conv.organization_id,
                    message_id=msg.id,
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    source_type="upload",
                    score=float(p.get("score") or 0),
                    excerpt=(p.get("content") or "")[:1000],
                    rank=int(p.get("rank") or 0),
                )
            )
        conv.updated_at = datetime.now(timezone.utc)
        # analytics
        try:
            from eaw.application.services.usage_service import UsageService

            UsageService(self.db).track(
                organization_id=conv.organization_id,
                user_id=conv.user_id,
                event_type="chat",
                model=model,
                input_tokens=None,
                output_tokens=token_count,
                metadata={
                    "conversation_id": str(conv.id),
                    "latency_ms": latency_ms,
                    "citations": len(passages),
                },
            )
        except Exception:  # noqa: BLE001
            pass
        self.db.commit()
        # reload with citations
        msg = self.db.scalar(
            select(Message)
            .options(selectinload(Message.citations))
            .where(Message.id == assistant_id)
        )
        assert msg is not None
        return msg

    def add_feedback(
        self,
        *,
        message_id: UUID,
        user_id: UUID,
        rating: int,
        comment: Optional[str] = None,
    ) -> MessageFeedback:
        if rating not in (-1, 1):
            raise ValidationAppError("rating must be +1 or -1")
        msg = self.db.get(Message, message_id)
        if msg is None:
            raise NotFoundError("Message not found")
        conv = self.db.get(Conversation, msg.conversation_id)
        if conv is None or conv.user_id != user_id:
            raise ForbiddenError("Not allowed")
        fb = MessageFeedback(
            organization_id=msg.organization_id,
            message_id=msg.id,
            user_id=user_id,
            rating=rating,
            comment=comment,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(fb)
        self.db.commit()
        self.db.refresh(fb)
        return fb
