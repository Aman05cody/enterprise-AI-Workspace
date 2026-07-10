"""Shared helpers for external connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from eaw.application.services.audit_service import AuditService
from eaw.application.services.document_service import DocumentService
from eaw.application.services.knowledge_service import KnowledgeService
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import (
    ConnectorStatus,
    MembershipRole,
    SyncJobStatus,
)
from eaw.domain.common.errors import ForbiddenError, NotFoundError, ValidationAppError
from eaw.domain.tenancy.policies import role_at_least
from eaw.infrastructure.db.models.connectors import (
    Connector,
    ConnectorResource,
    ConnectorSyncJob,
)
from eaw.infrastructure.db.models.knowledge import KnowledgeBase
from eaw.infrastructure.security.crypto import decrypt_secret, encrypt_secret


class ConnectorServiceBase:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        org_service: OrgService,
        knowledge_service: KnowledgeService,
        document_service: DocumentService,
        audit: AuditService,
        connector_type: str,
    ) -> None:
        self.db = db
        self.settings = settings
        self.org = org_service
        self.knowledge = knowledge_service
        self.documents = document_service
        self.audit = audit
        self.connector_type = connector_type

    def require_admin(self, org_id: UUID, user_id: UUID):
        mem = self.org.get_membership(org_id, user_id)
        if not role_at_least(mem.role, MembershipRole.ADMIN):
            raise ForbiddenError("Admin role required to manage connectors")
        return mem

    def get_connector(self, connector_id: UUID) -> Connector:
        c = self.db.get(Connector, connector_id)
        if c is None or c.type != self.connector_type:
            raise NotFoundError(f"{self.connector_type} connector not found")
        return c

    def decrypt_token(self, connector: Connector) -> str:
        if not connector.credentials_enc:
            raise ValidationAppError("Connector has no credentials")
        return decrypt_secret(connector.credentials_enc)

    def encrypt_token(self, token: str) -> str:
        return encrypt_secret(token)

    def upsert_connector(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        display_name: str,
        token: str,
        config: Optional[dict] = None,
    ) -> Connector:
        self.require_admin(organization_id, user_id)
        existing = self.db.scalar(
            select(Connector).where(
                Connector.organization_id == organization_id,
                Connector.type == self.connector_type,
            )
        )
        enc = self.encrypt_token(token)
        if existing:
            existing.credentials_enc = enc
            existing.status = ConnectorStatus.CONNECTED.value
            existing.display_name = display_name
            existing.config = {**(existing.config or {}), **(config or {})}
            connector = existing
        else:
            connector = Connector(
                organization_id=organization_id,
                type=self.connector_type,
                status=ConnectorStatus.CONNECTED.value,
                display_name=display_name,
                credentials_enc=enc,
                config=config or {},
                created_by=user_id,
            )
            self.db.add(connector)
        self.db.commit()
        self.db.refresh(connector)
        return connector

    def disconnect(self, *, connector_id: UUID, user_id: UUID) -> None:
        c = self.get_connector(connector_id)
        self.require_admin(c.organization_id, user_id)
        c.status = ConnectorStatus.DISCONNECTED.value
        c.credentials_enc = None
        self.audit.log(
            action=f"connector.{self.connector_type}.disconnected",
            actor_user_id=user_id,
            organization_id=c.organization_id,
            resource_type="connector",
            resource_id=c.id,
        )
        self.db.commit()

    def list_connectors(self, *, organization_id: UUID, user_id: UUID) -> list[Connector]:
        self.org.get_membership(organization_id, user_id)
        return list(
            self.db.scalars(
                select(Connector).where(
                    Connector.organization_id == organization_id,
                    Connector.type == self.connector_type,
                )
            ).all()
        )

    def list_resources(self, *, connector_id: UUID, user_id: UUID) -> list[ConnectorResource]:
        c = self.get_connector(connector_id)
        self.org.get_membership(c.organization_id, user_id)
        return list(
            self.db.scalars(
                select(ConnectorResource)
                .where(ConnectorResource.connector_id == c.id)
                .order_by(ConnectorResource.name)
            ).all()
        )

    def set_selection(
        self,
        *,
        connector_id: UUID,
        user_id: UUID,
        resource_ids: list[UUID],
    ) -> list[ConnectorResource]:
        c = self.get_connector(connector_id)
        self.require_admin(c.organization_id, user_id)
        resources = list(
            self.db.scalars(
                select(ConnectorResource).where(ConnectorResource.connector_id == c.id)
            ).all()
        )
        selected = set(resource_ids)
        for r in resources:
            r.sync_enabled = r.id in selected
        self.db.commit()
        return [r for r in resources if r.sync_enabled]

    def create_sync_job(
        self,
        *,
        connector: Connector,
        resource_id: Optional[UUID] = None,
    ) -> ConnectorSyncJob:
        job = ConnectorSyncJob(
            id=uuid4(),
            organization_id=connector.organization_id,
            connector_id=connector.id,
            resource_id=resource_id,
            status=SyncJobStatus.QUEUED.value,
            stats={},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(job)
        connector.status = ConnectorStatus.SYNCING.value
        self.db.commit()
        self.db.refresh(job)
        return job

    def ensure_kb(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
    ) -> KnowledgeBase:
        name = name[:200]
        existing = self.db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.organization_id == organization_id,
                KnowledgeBase.name == name,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
        if existing:
            return existing
        return self.knowledge.create(
            organization_id=organization_id,
            user_id=user_id,
            name=name,
            description=description,
        )

    def enabled_resources(
        self, connector_id: UUID, resource_id: Optional[UUID] = None
    ) -> list[ConnectorResource]:
        q = select(ConnectorResource).where(
            ConnectorResource.connector_id == connector_id,
            ConnectorResource.sync_enabled.is_(True),
        )
        if resource_id:
            q = q.where(ConnectorResource.id == resource_id)
        return list(self.db.scalars(q).all())
