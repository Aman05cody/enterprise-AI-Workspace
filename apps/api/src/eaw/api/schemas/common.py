"""Shared response envelopes."""

from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None


class DataResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta = Field(default_factory=Meta)


class MessageResponse(BaseModel):
    data: dict[str, Any]
    meta: Meta = Field(default_factory=Meta)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    email_verified_at: Optional[str] = None
    is_active: bool

    @classmethod
    def from_model(cls, user: Any) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            email_verified_at=(
                user.email_verified_at.isoformat() if user.email_verified_at else None
            ),
            is_active=user.is_active,
        )
