"""Audit logging service."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from eaw.infrastructure.db.models.audit import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        action: str,
        actor_user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        entry = AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(entry)
