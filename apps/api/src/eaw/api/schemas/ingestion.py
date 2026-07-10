"""Ingestion job schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IngestionJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    document_id: UUID
    celery_task_id: Optional[str] = None
    status: str
    stage: Optional[str] = None
    progress_pct: int
    attempt: int
    error_message: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)


class SemanticSearchHit(BaseModel):
    chunk_id: str
    score: float
    document_id: Optional[str] = None
    title: Optional[str] = None
    content_preview: Optional[str] = None
    chunk_index: Optional[int] = None
