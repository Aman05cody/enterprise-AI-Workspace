"""Slack connector: channels sync + AI summaries/search/recap."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from eaw.application.ports.llm import ChatMessage, LLMPort
from eaw.application.services.audit_service import AuditService
from eaw.application.services.chat_service import ChatService
from eaw.application.services.connector_base import ConnectorServiceBase
from eaw.application.services.document_service import DocumentService
from eaw.application.services.knowledge_service import KnowledgeService
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import ConnectorStatus, ConnectorType, SourceType, SyncJobStatus
from eaw.domain.common.errors import NotFoundError, ValidationAppError
from eaw.infrastructure.connectors.slack_client import SlackClient
from eaw.infrastructure.db.models.connectors import Connector, ConnectorResource, ConnectorSyncJob

logger = logging.getLogger(__name__)


class SlackService(ConnectorServiceBase):
    def __init__(
        self,
        db,
        settings: Settings,
        org_service: OrgService,
        knowledge_service: KnowledgeService,
        document_service: DocumentService,
        audit: AuditService,
        llm: LLMPort,
        chat_service: Optional[ChatService] = None,
    ) -> None:
        super().__init__(
            db,
            settings,
            org_service,
            knowledge_service,
            document_service,
            audit,
            ConnectorType.SLACK.value,
        )
        self.llm = llm
        self.chat = chat_service

    def _client(self, connector: Connector) -> SlackClient:
        return SlackClient(
            self.decrypt_token(connector),
            api_base=self.settings.slack_api_base,
        )

    def connect(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        bot_token: str,
        display_name: Optional[str] = None,
    ) -> Connector:
        client = SlackClient(bot_token, api_base=self.settings.slack_api_base)
        auth = client.verify_token()
        team = auth.get("team") or "Slack"
        connector = self.upsert_connector(
            organization_id=organization_id,
            user_id=user_id,
            display_name=display_name or f"Slack · {team}",
            token=bot_token.strip(),
            config={
                "team": team,
                "team_id": auth.get("team_id"),
                "user": auth.get("user"),
                "bot_id": auth.get("bot_id"),
            },
        )
        self.audit.log(
            action="connector.slack.connected",
            actor_user_id=user_id,
            organization_id=organization_id,
            resource_type="connector",
            resource_id=connector.id,
            metadata={"team": team},
        )
        self.db.commit()
        self.refresh_catalog(connector_id=connector.id, user_id=user_id)
        self.db.refresh(connector)
        return connector

    def refresh_catalog(self, *, connector_id: UUID, user_id: UUID) -> list[ConnectorResource]:
        c = self.get_connector(connector_id)
        self.require_admin(c.organization_id, user_id)
        if c.status != ConnectorStatus.CONNECTED.value:
            raise ValidationAppError("Connector is not connected")
        client = self._client(c)
        channels = client.list_channels(limit=100)
        existing = {
            r.external_id: r
            for r in self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        }
        for ch in channels:
            meta = {
                "name": ch.name,
                "is_private": ch.is_private,
                "num_members": ch.num_members,
                "topic": ch.topic,
                "purpose": ch.purpose,
            }
            if ch.id in existing:
                existing[ch.id].name = f"#{ch.name}"
                existing[ch.id].metadata_ = meta
            else:
                self.db.add(
                    ConnectorResource(
                        connector_id=c.id,
                        organization_id=c.organization_id,
                        external_id=ch.id,
                        name=f"#{ch.name}",
                        resource_type="channel",
                        sync_enabled=False,
                        metadata_=meta,
                    )
                )
        self.db.commit()
        return self.list_resources(connector_id=c.id, user_id=user_id)

    def sync(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        resource_id: Optional[UUID] = None,
    ) -> ConnectorSyncJob:
        c = self.get_connector(connector_id)
        self.require_admin(c.organization_id, user_id)
        job = self.create_sync_job(connector=c, resource_id=resource_id)
        try:
            from eaw.infrastructure.queue.enqueue import enqueue_slack_sync

            task_id = enqueue_slack_sync(job.id)
            if task_id:
                job.stats = {**(job.stats or {}), "celery_task_id": task_id}
                self.db.commit()
            else:
                self.db.refresh(job)
        except Exception:
            self.run_sync_job(job.id, actor_user_id=user_id)
            self.db.refresh(job)
        return job

    def run_sync_job(
        self, job_id: UUID, actor_user_id: Optional[UUID] = None
    ) -> ConnectorSyncJob:
        job = self.db.get(ConnectorSyncJob, job_id)
        if job is None:
            raise NotFoundError("Sync job not found")
        connector = self.get_connector(job.connector_id)
        job.status = SyncJobStatus.RUNNING.value
        self.db.commit()

        actor = actor_user_id or connector.created_by
        if not actor:
            job.status = SyncJobStatus.FAILED.value
            job.error_message = "No actor user for sync"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        resources = self.enabled_resources(connector.id, job.resource_id)
        if not resources:
            job.status = SyncJobStatus.FAILED.value
            job.error_message = "No Slack channels selected"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        client = self._client(connector)
        kb = self.ensure_kb(
            organization_id=connector.organization_id,
            user_id=actor,
            name="Slack Workspace",
            description="Channel history synced from Slack",
        )
        docs = 0
        errors: list[str] = []
        try:
            for res in resources:
                try:
                    msgs = client.history(
                        res.external_id,
                        limit=self.settings.slack_sync_max_messages,
                    )
                    name = (res.metadata_ or {}).get("name") or res.name
                    text = client.messages_to_text(msgs, channel_name=str(name).lstrip("#"))
                    if not text.strip():
                        continue
                    doc = self.documents.ingest_text(
                        kb_id=kb.id,
                        user_id=actor,
                        title=f"Slack · {res.name}",
                        text=text,
                        source_type=SourceType.SLACK.value,
                        source_path=res.external_id,
                        skip_duplicate=True,
                    )
                    if doc:
                        docs += 1
                    res.knowledge_base_id = kb.id
                    res.last_synced_at = datetime.now(timezone.utc)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Slack channel sync failed %s: %s", res.name, exc)
                    errors.append(f"{res.name}: {exc}")

            job.status = SyncJobStatus.SUCCEEDED.value
            job.stats = {
                "channels": len(resources),
                "documents": docs,
                "errors": errors[:20],
                "knowledge_base_id": str(kb.id),
            }
            job.error_message = None if not errors else f"{len(errors)} channel errors"
            job.finished_at = datetime.now(timezone.utc)
            connector.last_synced_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.audit.log(
                action="connector.slack.synced",
                actor_user_id=actor,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector.id,
                metadata=job.stats,
            )
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Slack sync failed")
            job.status = SyncJobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.ERROR.value
            self.db.commit()
        self.db.refresh(job)
        return job

    def _get_resource(self, resource_id: UUID) -> ConnectorResource:
        r = self.db.get(ConnectorResource, resource_id)
        if r is None:
            raise NotFoundError("Channel resource not found")
        return r

    def channel_summary(
        self, *, connector_id: UUID, user_id: UUID, resource_id: UUID, limit: int = 100
    ) -> dict:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        res = self._get_resource(resource_id)
        if res.connector_id != c.id:
            raise NotFoundError("Channel not in connector")
        client = self._client(c)
        msgs = client.history(res.external_id, limit=limit)
        name = (res.metadata_ or {}).get("name") or res.name
        text = client.messages_to_text(msgs, channel_name=str(name).lstrip("#"))
        result = self.llm.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Summarize this Slack channel discussion for a busy manager. "
                        "Include key decisions, action items, open questions, and risks. "
                        "Use bullet points. Do not invent messages not present."
                    ),
                ),
                ChatMessage(role="user", content=text[:25000] or "No messages."),
            ],
            temperature=0.2,
        )
        return {
            "channel": res.name,
            "message_count": len(msgs),
            "summary": result.content,
            "model": result.model,
        }

    def meeting_recap(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        resource_id: UUID,
        thread_ts: Optional[str] = None,
        limit: int = 150,
    ) -> dict:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        res = self._get_resource(resource_id)
        client = self._client(c)
        if thread_ts:
            msgs = client.replies(res.external_id, thread_ts, limit=limit)
            label = f"thread {thread_ts}"
        else:
            msgs = client.history(res.external_id, limit=limit)
            label = "recent channel history"
        text = client.messages_to_text(msgs, channel_name=res.name)
        result = self.llm.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Write a meeting/thread recap: agenda themes, decisions, "
                        "action items (owner if mentioned), and follow-ups. "
                        "Ground only in the provided messages."
                    ),
                ),
                ChatMessage(role="user", content=f"Source: {label}\n\n{text[:25000]}"),
            ],
            temperature=0.2,
        )
        return {
            "channel": res.name,
            "source": label,
            "recap": result.content,
            "model": result.model,
        }

    def ai_search(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        query: str,
    ) -> dict:
        """Search indexed Slack KB via chat RAG when available."""
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        # find KB from any synced channel
        res = self.db.scalar(
            select(ConnectorResource).where(
                ConnectorResource.connector_id == c.id,
                ConnectorResource.knowledge_base_id.is_not(None),
            )
        )
        if not res or not res.knowledge_base_id:
            raise ValidationAppError("Sync at least one channel before AI search")
        if not self.chat:
            raise ValidationAppError("Chat service unavailable")
        conv = self.chat.create_conversation(
            kb_id=res.knowledge_base_id,
            user_id=user_id,
            title=f"Slack search: {query[:60]}",
        )
        result = self.chat.ask(
            conversation_id=conv.id,
            user_id=user_id,
            content=query,
            stream=False,
        )
        assert isinstance(result, dict)
        msg = result["message"]
        return {
            "conversation_id": str(conv.id),
            "knowledge_base_id": str(res.knowledge_base_id),
            "answer": msg.content,
            "confidence": msg.confidence,
            "insufficient_context": result.get("insufficient_context"),
        }
