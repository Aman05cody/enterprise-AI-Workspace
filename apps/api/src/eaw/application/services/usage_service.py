"""Usage event recording (analytics / billing hooks)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from eaw.infrastructure.db.models.analytics import UsageEvent


class UsageService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def track(
        self,
        *,
        organization_id: UUID,
        event_type: str,
        user_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        model: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        commit: bool = False,
    ) -> UsageEvent:
        event = UsageEvent(
            id=uuid4(),
            organization_id=organization_id,
            user_id=user_id,
            department_id=department_id,
            event_type=event_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata_=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        if commit:
            self.db.commit()
            self.db.refresh(event)
        return event
