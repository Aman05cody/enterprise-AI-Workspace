"""Knowledge base use cases."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from eaw.application.services.audit_service import AuditService
from eaw.application.services.org_service import OrgService
from eaw.domain.common.enums import DocumentStatus, MembershipRole
from eaw.domain.common.errors import ConflictError, NotFoundError, ValidationAppError
from eaw.domain.tenancy.policies import (
    can_delete_knowledge_bases,
    can_manage_knowledge_bases,
    can_read_knowledge,
    require_role,
)
from eaw.infrastructure.db.models.knowledge import Document, KnowledgeBase
from eaw.infrastructure.db.models.tenancy import Department


class KnowledgeService:
    def __init__(
        self,
        db: Session,
        org_service: OrgService,
        audit: AuditService,
    ) -> None:
        self.db = db
        self.org = org_service
        self.audit = audit

    def _get_kb(self, kb_id: UUID) -> KnowledgeBase:
        kb = self.db.get(KnowledgeBase, kb_id)
        if kb is None or kb.deleted_at is not None:
            raise NotFoundError("Knowledge base not found")
        return kb

    def create(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        department_id: Optional[UUID] = None,
    ) -> KnowledgeBase:
        mem = self.org.get_membership(organization_id, user_id)
        if not can_manage_knowledge_bases(mem.role):
            require_role(mem.role, MembershipRole.MANAGER, action="create knowledge bases")

        name = name.strip()
        if not name:
            raise ValidationAppError("Name is required")

        if department_id:
            dept = self.db.get(Department, department_id)
            if (
                dept is None
                or dept.organization_id != organization_id
                or dept.deleted_at is not None
            ):
                raise NotFoundError("Department not found")

        existing = self.db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.organization_id == organization_id,
                KnowledgeBase.name == name,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
        if existing:
            raise ConflictError("A knowledge base with this name already exists")

        kb = KnowledgeBase(
            organization_id=organization_id,
            department_id=department_id,
            name=name,
            description=description,
            settings={
                "chunk_size": 800,
                "chunk_overlap": 120,
            },
            created_by=user_id,
        )
        self.db.add(kb)
        self.audit.log(
            action="kb.created",
            actor_user_id=user_id,
            organization_id=organization_id,
            resource_type="knowledge_base",
            metadata={"name": name},
        )
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def list(
        self, *, organization_id: UUID, user_id: UUID
    ) -> list[tuple[KnowledgeBase, dict]]:
        mem = self.org.get_membership(organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="list knowledge bases")

        kbs = list(
            self.db.scalars(
                select(KnowledgeBase)
                .where(
                    KnowledgeBase.organization_id == organization_id,
                    KnowledgeBase.deleted_at.is_(None),
                )
                .order_by(KnowledgeBase.name)
            ).all()
        )
        result: list[tuple[KnowledgeBase, dict]] = []
        for kb in kbs:
            stats = self._stats(kb.id)
            result.append((kb, stats))
        return result

    def get(
        self, *, kb_id: UUID, user_id: UUID
    ) -> tuple[KnowledgeBase, dict]:
        kb = self._get_kb(kb_id)
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="view knowledge base")
        return kb, self._stats(kb.id)

    def update(
        self,
        *,
        kb_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        department_id: Optional[UUID] = None,
        settings: Optional[dict] = None,
    ) -> KnowledgeBase:
        kb = self._get_kb(kb_id)
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_manage_knowledge_bases(mem.role):
            require_role(mem.role, MembershipRole.MANAGER, action="update knowledge bases")

        if name is not None:
            kb.name = name.strip()
        if description is not None:
            kb.description = description
        if department_id is not None:
            kb.department_id = department_id or None
        if settings is not None:
            kb.settings = {**(kb.settings or {}), **settings}

        self.audit.log(
            action="kb.updated",
            actor_user_id=user_id,
            organization_id=kb.organization_id,
            resource_type="knowledge_base",
            resource_id=kb.id,
        )
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def soft_delete(self, *, kb_id: UUID, user_id: UUID) -> None:
        from datetime import datetime, timezone

        kb = self._get_kb(kb_id)
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_delete_knowledge_bases(mem.role):
            require_role(mem.role, MembershipRole.ADMIN, action="delete knowledge bases")

        kb.deleted_at = datetime.now(timezone.utc)
        # soft-delete documents
        docs = self.db.scalars(
            select(Document).where(
                Document.knowledge_base_id == kb.id,
                Document.deleted_at.is_(None),
            )
        ).all()
        now = datetime.now(timezone.utc)
        for d in docs:
            d.deleted_at = now
            d.status = DocumentStatus.DELETED.value

        self.audit.log(
            action="kb.deleted",
            actor_user_id=user_id,
            organization_id=kb.organization_id,
            resource_type="knowledge_base",
            resource_id=kb.id,
        )
        self.db.commit()

    def _stats(self, kb_id: UUID) -> dict:
        rows = self.db.execute(
            select(Document.status, func.count())
            .where(
                Document.knowledge_base_id == kb_id,
                Document.deleted_at.is_(None),
            )
            .group_by(Document.status)
        ).all()
        by_status = {status: count for status, count in rows}
        total = sum(by_status.values())
        return {
            "document_count": total,
            "by_status": by_status,
            "pending": by_status.get(DocumentStatus.PENDING.value, 0),
            "ready": by_status.get(DocumentStatus.READY.value, 0),
            "failed": by_status.get(DocumentStatus.FAILED.value, 0),
            "processing": by_status.get(DocumentStatus.PROCESSING.value, 0),
        }
