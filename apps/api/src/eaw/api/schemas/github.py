"""GitHub connector schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GitHubConnectRequest(BaseModel):
    organization_id: UUID
    personal_access_token: str = Field(min_length=8, max_length=500)
    display_name: Optional[str] = None


class ConnectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    type: str
    status: str
    display_name: str
    config: dict[str, Any] = Field(default_factory=dict)
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ConnectorResourceOut(BaseModel):
    id: UUID
    connector_id: UUID
    external_id: str
    name: str
    resource_type: str
    sync_enabled: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    knowledge_base_id: Optional[UUID] = None
    last_synced_at: Optional[datetime] = None


class ResourceSelectionRequest(BaseModel):
    resource_ids: list[UUID]


class SyncRequest(BaseModel):
    resource_id: Optional[UUID] = None


class SyncJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_id: UUID
    resource_id: Optional[UUID] = None
    status: str
    stats: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class PRReviewRequest(BaseModel):
    connector_id: UUID
    owner: str
    repo: str
    pull_number: int = Field(ge=1)


class ExplainRequest(BaseModel):
    connector_id: UUID
    owner: str
    repo: str
    path: str
    ref: Optional[str] = None
    focus: Optional[str] = None


class GenerateRequest(BaseModel):
    connector_id: UUID
    owner: str
    repo: str
    path: str
    ref: Optional[str] = None


class RepoChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[UUID] = None
