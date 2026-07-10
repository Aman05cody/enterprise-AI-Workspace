"""Conversation and chat routes (incl. SSE streaming)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from eaw.api.deps import ChatSvc, CurrentUser
from eaw.api.schemas.chat import (
    CitationOut,
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    FeedbackRequest,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
)
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta

router = APIRouter(tags=["chat"])


def _conv_out(c) -> ConversationOut:
    return ConversationOut.model_validate(c)


def _msg_out(m) -> MessageOut:
    citations = [
        CitationOut(
            id=c.id,
            document_id=c.document_id,
            chunk_id=c.chunk_id,
            score=c.score,
            excerpt=c.excerpt,
            rank=c.rank,
            source_type=c.source_type,
        )
        for c in (m.citations or [])
    ]
    return MessageOut(
        id=m.id,
        conversation_id=m.conversation_id,
        role=m.role,
        content=m.content,
        confidence=m.confidence,
        token_count=m.token_count,
        latency_ms=m.latency_ms,
        model=m.model,
        created_at=m.created_at,
        citations=citations,
    )


@router.post(
    "/conversations",
    response_model=DataResponse[ConversationOut],
    status_code=201,
)
def create_conversation(
    body: ConversationCreate,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> DataResponse[ConversationOut]:
    conv = chat.create_conversation(
        kb_id=body.knowledge_base_id, user_id=user.id, title=body.title
    )
    return DataResponse(
        data=_conv_out(conv),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/knowledge-bases/{kb_id}/conversations",
    response_model=DataResponse[list[ConversationOut]],
)
def list_conversations(
    kb_id: UUID,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> DataResponse[list[ConversationOut]]:
    rows = chat.list_conversations(kb_id=kb_id, user_id=user.id)
    return DataResponse(
        data=[_conv_out(c) for c in rows],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(rows)
        ),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=DataResponse[ConversationOut],
)
def get_conversation(
    conversation_id: UUID,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> DataResponse[ConversationOut]:
    conv = chat.get_conversation(conversation_id, user.id)
    return DataResponse(
        data=_conv_out(conv),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=DataResponse[ConversationOut],
)
def rename_conversation(
    conversation_id: UUID,
    body: ConversationUpdate,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> DataResponse[ConversationOut]:
    conv = chat.rename_conversation(conversation_id, user.id, body.title)
    return DataResponse(
        data=_conv_out(conv),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=MessageResponse,
)
def delete_conversation(
    conversation_id: UUID,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> MessageResponse:
    chat.delete_conversation(conversation_id, user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=DataResponse[list[MessageOut]],
)
def list_messages(
    conversation_id: UUID,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> DataResponse[list[MessageOut]]:
    msgs = chat.list_messages(conversation_id, user.id)
    return DataResponse(
        data=[_msg_out(m) for m in msgs],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(msgs)
        ),
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=DataResponse[SendMessageResponse],
)
def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> DataResponse[SendMessageResponse]:
    result = chat.ask(
        conversation_id=conversation_id,
        user_id=user.id,
        content=body.content,
        stream=False,
    )
    assert isinstance(result, dict)
    msg = result["message"]
    return DataResponse(
        data=SendMessageResponse(
            message=_msg_out(msg),
            confidence=result.get("confidence"),
            suggestions=result.get("suggestions") or [],
            insufficient_context=bool(result.get("insufficient_context")),
        ),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/conversations/{conversation_id}/messages:stream")
def send_message_stream(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: CurrentUser,
    chat: ChatSvc,
) -> StreamingResponse:
    events = chat.ask(
        conversation_id=conversation_id,
        user_id=user.id,
        content=body.content,
        stream=True,
    )

    def generate():
        assert events is not None
        for item in events:  # type: ignore[union-attr]
            yield _sse(item["event"], item["data"])

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/messages/{message_id}/feedback",
    response_model=MessageResponse,
    status_code=201,
)
def feedback(
    message_id: UUID,
    body: FeedbackRequest,
    request: Request,
    user: CurrentUser,
    chat: ChatSvc,
) -> MessageResponse:
    chat.add_feedback(
        message_id=message_id,
        user_id=user.id,
        rating=body.rating,
        comment=body.comment,
    )
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )
