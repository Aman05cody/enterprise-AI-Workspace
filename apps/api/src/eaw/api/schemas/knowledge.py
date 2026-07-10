"""Knowledge base and document schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    department_id: Optional[UUID] = None


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    department_id: Optional[UUID] = None
    settings: Optional[dict[str, Any]] = None


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    department_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)
    stats: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    knowledge_base_id: UUID
    title: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    status: str
    source_type: str
    current_version: int
    chunk_count: int
    ai_summary: Optional[str] = None
    ai_tags: list[Any] = Field(default_factory=list)
    uploaded_by: Optional[UUID] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class DocumentPreviewOut(BaseModel):
    document_id: UUID
    title: str
    content_type: str
    preview_text: Optional[str] = None
    has_preview: bool
    status: str
    current_version: int


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version_number: int
    checksum_sha256: str
    content_type: str
    file_size_bytes: int
    original_filename: str
    created_by: Optional[UUID] = None
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    knowledge_base_id: Optional[UUID] = None
    limit: int = Field(default=20, ge=1, le=50)


class DocumentSearchHit(BaseModel):
    document: DocumentOut
    snippet: Optional[str] = None
