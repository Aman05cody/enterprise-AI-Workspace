"""Shared connector schemas for Notion / Drive / etc."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class NotionConnectRequest(BaseModel):
    organization_id: UUID
    integration_token: str = Field(min_length=10, max_length=500)
    display_name: Optional[str] = None


class DriveConnectRequest(BaseModel):
    organization_id: UUID
    access_token: str = Field(min_length=10, max_length=4096)
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    display_name: Optional[str] = None


class SlackConnectRequest(BaseModel):
    organization_id: UUID
    bot_token: str = Field(min_length=10, max_length=500)
    display_name: Optional[str] = None


class JiraConnectRequest(BaseModel):
    organization_id: UUID
    base_url: str = Field(min_length=8, max_length=500)
    email: str = Field(min_length=3, max_length=320)
    api_token: str = Field(min_length=8, max_length=500)
    display_name: Optional[str] = None


class SlackChannelSummaryRequest(BaseModel):
    resource_id: UUID
    limit: int = Field(default=100, ge=10, le=500)


class SlackMeetingRecapRequest(BaseModel):
    resource_id: UUID
    thread_ts: Optional[str] = None
    limit: int = Field(default=150, ge=10, le=500)


class SlackSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class JiraStoryRequest(BaseModel):
    issue_key: str = Field(min_length=2, max_length=32)


class JiraSearchRequest(BaseModel):
    jql: str = Field(min_length=1, max_length=2000)
    max_results: int = Field(default=20, ge=1, le=50)


class JiraSprintSummaryRequest(BaseModel):
    project_key: str = Field(min_length=1, max_length=32)
    board_id: Optional[int] = None
