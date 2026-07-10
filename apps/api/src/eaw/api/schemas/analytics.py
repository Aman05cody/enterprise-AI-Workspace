"""Analytics and audit schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OverviewOut(BaseModel):
    period_days: int
    members: int
    active_users: int
    knowledge_bases: int
    documents: int
    storage_bytes: int
    chat_messages: int
    usage_by_type: dict[str, int] = Field(default_factory=dict)
    tokens_in: int
    tokens_out: int
    tokens_total: int


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: Optional[UUID] = None
    actor_user_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
