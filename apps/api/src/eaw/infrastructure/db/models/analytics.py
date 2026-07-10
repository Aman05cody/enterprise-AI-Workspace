"""Usage analytics models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Integer, String, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from eaw.infrastructure.db.base import Base, UUIDPrimaryKeyMixin


class UsageEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "usage_events"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    department_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class OrganizationUsageCounter(Base):
    """Billing-ready rollup counters (optional period aggregation)."""

    __tablename__ = "organization_usage_counters"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    messages_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_in: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    documents_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
