"""Chat schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    knowledge_base_id: UUID
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    knowledge_base_id: UUID
    user_id: UUID
    title: Optional[str] = None
    memory_summary: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: Optional[UUID] = None
    chunk_id: Optional[UUID] = None
    score: Optional[float] = None
    excerpt: str
    rank: int
    source_type: str = "upload"


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    confidence: Optional[float] = None
    token_count: Optional[int] = None
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    created_at: datetime
    citations: list[CitationOut] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    options: Optional[dict[str, Any]] = None


class SendMessageResponse(BaseModel):
    message: MessageOut
    confidence: Optional[float] = None
    suggestions: list[str] = Field(default_factory=list)
    insufficient_context: bool = False


class FeedbackRequest(BaseModel):
    rating: int = Field(description="+1 or -1")
    comment: Optional[str] = None
