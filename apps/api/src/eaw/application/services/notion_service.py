"""Notion connector service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from eaw.application.services.audit_service import AuditService
from eaw.application.services.connector_base import ConnectorServiceBase
from eaw.application.services.document_service import DocumentService
from eaw.application.services.knowledge_service import KnowledgeService
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import ConnectorStatus, ConnectorType, SourceType, SyncJobStatus
from eaw.domain.common.errors import ValidationAppError
from eaw.infrastructure.connectors.notion_client import NotionClient
from eaw.infrastructure.db.models.connectors import Connector, ConnectorResource, ConnectorSyncJob

logger = logging.getLogger(__name__)


class NotionService(ConnectorServiceBase):
    def __init__(
        self,
        db,
        settings: Settings,
        org_service: OrgService,
        knowledge_service: KnowledgeService,
        document_service: DocumentService,
        audit: AuditService,
    ) -> None:
        super().__init__(
            db,
            settings,
            org_service,
            knowledge_service,
            document_service,
            audit,
            ConnectorType.NOTION.value,
        )

    def _client(self, connector: Connector) -> NotionClient:
        return NotionClient(
            self.decrypt_token(connector),
            api_base=self.settings.notion_api_base,
            api_version=self.settings.notion_api_version,
        )

    def connect(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        integration_token: str,
        display_name: Optional[str] = None,
    ) -> Connector:
        client = NotionClient(
            integration_token,
            api_base=self.settings.notion_api_base,
            api_version=self.settings.notion_api_version,
        )
        profile = client.verify_token()
        name = display_name or "Notion Workspace"
        if isinstance(profile, dict) and profile.get("name"):
            name = display_name or f"Notion · {profile.get('name')}"
        connector = self.upsert_connector(
            organization_id=organization_id,
            user_id=user_id,
            display_name=name,
            token=integration_token.strip(),
            config={"bot": profile if isinstance(profile, dict) else {}},
        )
        self.audit.log(
            action="connector.notion.connected",
            actor_user_id=user_id,
            organization_id=organization_id,
            resource_type="connector",
            resource_id=connector.id,
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
        pages = client.list_pages(max_pages=self.settings.notion_sync_max_pages)
        existing = {
            r.external_id: r
            for r in self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        }
        for page in pages:
            meta = {
                "title": page.title,
                "url": page.url,
                "last_edited_time": page.last_edited_time,
                "object_type": page.object_type,
            }
            if page.id in existing:
                existing[page.id].name = page.title
                existing[page.id].metadata_ = meta
            else:
                self.db.add(
                    ConnectorResource(
                        connector_id=c.id,
                        organization_id=c.organization_id,
                        external_id=page.id,
                        name=page.title,
                        resource_type="page",
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
            from eaw.infrastructure.queue.enqueue import enqueue_notion_sync

            task_id = enqueue_notion_sync(job.id)
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
            from eaw.domain.common.errors import NotFoundError

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
            job.error_message = "No Notion pages selected for sync"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        client = self._client(connector)
        kb = self.ensure_kb(
            organization_id=connector.organization_id,
            user_id=actor,
            name="Notion Workspace",
            description="Pages synced from Notion",
        )
        docs = 0
        errors: list[str] = []
        try:
            for res in resources:
                try:
                    title = res.name or "Untitled"
                    md = client.page_to_markdown(res.external_id, title=title)
                    header = (
                        f"Source: Notion\n"
                        f"Page ID: {res.external_id}\n"
                        f"URL: {(res.metadata_ or {}).get('url') or ''}\n\n"
                    )
                    doc = self.documents.ingest_text(
                        kb_id=kb.id,
                        user_id=actor,
                        title=f"Notion · {title}",
                        text=header + md,
                        source_type=SourceType.NOTION.value,
                        source_path=res.external_id,
                        skip_duplicate=True,
                    )
                    if doc:
                        docs += 1
                    res.knowledge_base_id = kb.id
                    res.last_synced_at = datetime.now(timezone.utc)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Notion page sync failed %s: %s", res.external_id, exc)
                    errors.append(f"{res.name}: {exc}")

            job.status = SyncJobStatus.SUCCEEDED.value
            job.stats = {
                "pages": len(resources),
                "documents": docs,
                "errors": errors[:20],
                "knowledge_base_id": str(kb.id),
            }
            job.error_message = None if not errors else f"{len(errors)} page errors"
            job.finished_at = datetime.now(timezone.utc)
            connector.last_synced_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.audit.log(
                action="connector.notion.synced",
                actor_user_id=actor,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector.id,
                metadata=job.stats,
            )
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Notion sync failed")
            job.status = SyncJobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.ERROR.value
            self.db.commit()
        self.db.refresh(job)
        return job
