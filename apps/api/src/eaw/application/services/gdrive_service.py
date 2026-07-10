"""Google Drive connector service."""

from __future__ import annotations

import json
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
from eaw.infrastructure.connectors.gdrive_client import GoogleDriveClient
from eaw.infrastructure.db.models.connectors import Connector, ConnectorResource, ConnectorSyncJob

logger = logging.getLogger(__name__)


class GoogleDriveService(ConnectorServiceBase):
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
            ConnectorType.GDRIVE.value,
        )

    def _client(self, connector: Connector) -> GoogleDriveClient:
        # credentials may be plain access token or JSON with access/refresh
        raw = self.decrypt_token(connector)
        access = raw
        refresh = None
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and payload.get("access_token"):
                access = payload["access_token"]
                refresh = payload.get("refresh_token")
        except json.JSONDecodeError:
            pass
        cfg = connector.config or {}
        return GoogleDriveClient(
            access,
            api_base=self.settings.gdrive_api_base,
            refresh_token=refresh,
            client_id=cfg.get("client_id") or None,
            client_secret=cfg.get("client_secret") or None,
        )

    def connect(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Connector:
        # Store JSON blob if refresh present
        if refresh_token:
            secret = json.dumps(
                {
                    "access_token": access_token.strip(),
                    "refresh_token": refresh_token.strip(),
                }
            )
        else:
            secret = access_token.strip()

        client = GoogleDriveClient(
            access_token,
            api_base=self.settings.gdrive_api_base,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
        about = client.verify_token()
        user = (about or {}).get("user") or {}
        email = user.get("emailAddress") or "drive"
        connector = self.upsert_connector(
            organization_id=organization_id,
            user_id=user_id,
            display_name=display_name or f"Google Drive · {email}",
            token=secret,
            config={
                "email": email,
                "display_name": user.get("displayName"),
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        # Don't persist client_secret in config in production ideally —
        # keep only if provided for refresh (encrypted token holds refresh).
        if client_secret:
            connector.config = {
                **(connector.config or {}),
                "client_id": client_id,
                # store secret encrypted separately would be better; config is DB-only admin
                "client_secret": client_secret,
            }
            self.db.commit()

        self.audit.log(
            action="connector.gdrive.connected",
            actor_user_id=user_id,
            organization_id=organization_id,
            resource_type="connector",
            resource_id=connector.id,
            metadata={"email": email},
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

        # Root folders + root-level indexable files as resources
        items = client.list_children(folder_id="root", page_size=100)
        existing = {
            r.external_id: r
            for r in self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        }

        # Always ensure root folder resource
        root_meta = {"name": "My Drive (root)", "is_folder": True, "folder_id": "root"}
        if "root" in existing:
            existing["root"].name = "My Drive (root)"
            existing["root"].metadata_ = root_meta
        else:
            self.db.add(
                ConnectorResource(
                    connector_id=c.id,
                    organization_id=c.organization_id,
                    external_id="root",
                    name="My Drive (root)",
                    resource_type="folder",
                    sync_enabled=False,
                    metadata_=root_meta,
                )
            )

        for item in items:
            if not item.is_folder:
                continue
            meta = {
                "name": item.name,
                "is_folder": True,
                "folder_id": item.id,
                "mime_type": item.mime_type,
                "web_view_link": item.web_view_link,
                "modified_time": item.modified_time,
            }
            if item.id in existing:
                existing[item.id].name = item.name
                existing[item.id].metadata_ = meta
            else:
                self.db.add(
                    ConnectorResource(
                        connector_id=c.id,
                        organization_id=c.organization_id,
                        external_id=item.id,
                        name=item.name,
                        resource_type="folder",
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
            from eaw.infrastructure.queue.enqueue import enqueue_gdrive_sync

            task_id = enqueue_gdrive_sync(job.id)
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
            job.error_message = "No Drive folders selected for sync"
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.db.commit()
            return job

        client = self._client(connector)
        kb = self.ensure_kb(
            organization_id=connector.organization_id,
            user_id=actor,
            name="Google Drive",
            description="Files synced from Google Drive",
        )
        docs = 0
        files_seen = 0
        errors: list[str] = []
        try:
            for res in resources:
                folder_id = (res.metadata_ or {}).get("folder_id") or res.external_id
                try:
                    files = client.list_files_recursive(
                        folder_id,
                        max_files=self.settings.gdrive_sync_max_files,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{res.name}: list failed: {exc}")
                    continue

                for f in files:
                    files_seen += 1
                    try:
                        text = client.download_text(
                            f.id,
                            f.mime_type,
                            max_bytes=self.settings.gdrive_sync_max_file_bytes,
                        )
                        header = (
                            f"Source: Google Drive\n"
                            f"File: {f.name}\n"
                            f"MIME: {f.mime_type}\n"
                            f"Link: {f.web_view_link or ''}\n\n"
                        )
                        doc = self.documents.ingest_text(
                            kb_id=kb.id,
                            user_id=actor,
                            title=f"Drive · {f.name}",
                            text=header + text,
                            source_type=SourceType.GDRIVE.value,
                            source_path=f.id,
                            skip_duplicate=True,
                        )
                        if doc:
                            docs += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Drive file sync failed %s: %s", f.name, exc)
                        errors.append(f"{f.name}: {exc}")

                res.knowledge_base_id = kb.id
                res.last_synced_at = datetime.now(timezone.utc)

            job.status = SyncJobStatus.SUCCEEDED.value
            job.stats = {
                "folders": len(resources),
                "files_seen": files_seen,
                "documents": docs,
                "errors": errors[:20],
                "knowledge_base_id": str(kb.id),
            }
            job.error_message = None if not errors else f"{len(errors)} file errors"
            job.finished_at = datetime.now(timezone.utc)
            connector.last_synced_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.CONNECTED.value
            self.audit.log(
                action="connector.gdrive.synced",
                actor_user_id=actor,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector.id,
                metadata=job.stats,
            )
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Drive sync failed")
            job.status = SyncJobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            connector.status = ConnectorStatus.ERROR.value
            self.db.commit()
        self.db.refresh(job)
        return job
