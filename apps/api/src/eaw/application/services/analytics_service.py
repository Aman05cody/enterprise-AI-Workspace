"""Organization analytics aggregations for admin dashboards."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from eaw.application.services.org_service import OrgService
from eaw.domain.common.enums import MembershipRole
from eaw.domain.common.errors import ForbiddenError
from eaw.domain.tenancy.policies import role_at_least
from eaw.infrastructure.db.models.analytics import UsageEvent
from eaw.infrastructure.db.models.audit import AuditLog
from eaw.infrastructure.db.models.conversation import Message, MessageCitation
from eaw.infrastructure.db.models.identity import User
from eaw.infrastructure.db.models.knowledge import Document, KnowledgeBase
from eaw.infrastructure.db.models.tenancy import Department, Membership


class AnalyticsService:
    def __init__(self, db: Session, org_service: OrgService) -> None:
        self.db = db
        self.org = org_service

    def _require_admin_or_manager(self, org_id: UUID, user_id: UUID) -> Membership:
        mem = self.org.get_membership(org_id, user_id)
        if not role_at_least(mem.role, MembershipRole.MANAGER):
            raise ForbiddenError("Manager or admin role required for analytics")
        return mem

    def overview(self, *, organization_id: UUID, user_id: UUID, days: int = 30) -> dict:
        self._require_admin_or_manager(organization_id, user_id)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        members = int(
            self.db.scalar(
                select(func.count())
                .select_from(Membership)
                .where(
                    Membership.organization_id == organization_id,
                    Membership.status == "active",
                )
            )
            or 0
        )
        docs = int(
            self.db.scalar(
                select(func.count())
                .select_from(Document)
                .where(
                    Document.organization_id == organization_id,
                    Document.deleted_at.is_(None),
                )
            )
            or 0
        )
        storage = int(
            self.db.scalar(
                select(func.coalesce(func.sum(Document.file_size_bytes), 0)).where(
                    Document.organization_id == organization_id,
                    Document.deleted_at.is_(None),
                )
            )
            or 0
        )
        kbs = int(
            self.db.scalar(
                select(func.count())
                .select_from(KnowledgeBase)
                .where(
                    KnowledgeBase.organization_id == organization_id,
                    KnowledgeBase.deleted_at.is_(None),
                )
            )
            or 0
        )
        chat_msgs = int(
            self.db.scalar(
                select(func.count())
                .select_from(Message)
                .where(
                    Message.organization_id == organization_id,
                    Message.role == "user",
                    Message.created_at >= since,
                )
            )
            or 0
        )
        usage_rows = self.db.execute(
            select(UsageEvent.event_type, func.count())
            .where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.created_at >= since,
            )
            .group_by(UsageEvent.event_type)
        ).all()
        usage_by_type = {t: int(c) for t, c in usage_rows}
        tokens_in = int(
            self.db.scalar(
                select(func.coalesce(func.sum(UsageEvent.input_tokens), 0)).where(
                    UsageEvent.organization_id == organization_id,
                    UsageEvent.created_at >= since,
                )
            )
            or 0
        )
        tokens_out = int(
            self.db.scalar(
                select(func.coalesce(func.sum(UsageEvent.output_tokens), 0)).where(
                    UsageEvent.organization_id == organization_id,
                    UsageEvent.created_at >= since,
                )
            )
            or 0
        )
        active_users = int(
            self.db.scalar(
                select(func.count(func.distinct(UsageEvent.user_id))).where(
                    UsageEvent.organization_id == organization_id,
                    UsageEvent.created_at >= since,
                    UsageEvent.user_id.is_not(None),
                )
            )
            or 0
        )

        return {
            "period_days": days,
            "members": members,
            "active_users": active_users,
            "knowledge_bases": kbs,
            "documents": docs,
            "storage_bytes": storage,
            "chat_messages": chat_msgs,
            "usage_by_type": usage_by_type,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_in + tokens_out,
        }

    def usage_timeseries(
        self, *, organization_id: UUID, user_id: UUID, days: int = 14
    ) -> list[dict]:
        self._require_admin_or_manager(organization_id, user_id)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = self.db.execute(
            select(
                func.date_trunc("day", UsageEvent.created_at).label("day"),
                UsageEvent.event_type,
                func.count(),
            )
            .where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.created_at >= since,
            )
            .group_by("day", UsageEvent.event_type)
            .order_by("day")
        ).all()

        by_day: dict[str, dict[str, Any]] = {}
        for day, event_type, count in rows:
            key = day.date().isoformat() if hasattr(day, "date") else str(day)[:10]
            if key not in by_day:
                by_day[key] = {"date": key, "total": 0}
            by_day[key][event_type] = int(count)
            by_day[key]["total"] += int(count)

        # fill empty days
        out = []
        for i in range(days, -1, -1):
            d = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
            out.append(by_day.get(d, {"date": d, "total": 0}))
        return out

    def popular_documents(
        self, *, organization_id: UUID, user_id: UUID, limit: int = 10
    ) -> list[dict]:
        self._require_admin_or_manager(organization_id, user_id)
        rows = self.db.execute(
            select(
                MessageCitation.document_id,
                func.count().label("citations"),
            )
            .where(
                MessageCitation.organization_id == organization_id,
                MessageCitation.document_id.is_not(None),
            )
            .group_by(MessageCitation.document_id)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        result = []
        for doc_id, citations in rows:
            doc = self.db.get(Document, doc_id)
            if not doc or doc.deleted_at is not None:
                continue
            result.append(
                {
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "status": doc.status,
                    "source_type": doc.source_type,
                    "citations": int(citations),
                    "file_size_bytes": doc.file_size_bytes,
                }
            )
        return result

    def department_activity(
        self, *, organization_id: UUID, user_id: UUID, days: int = 30
    ) -> list[dict]:
        self._require_admin_or_manager(organization_id, user_id)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        depts = list(
            self.db.scalars(
                select(Department).where(
                    Department.organization_id == organization_id,
                    Department.deleted_at.is_(None),
                )
            ).all()
        )
        # usage events with department_id
        rows = self.db.execute(
            select(UsageEvent.department_id, func.count())
            .where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.created_at >= since,
                UsageEvent.department_id.is_not(None),
            )
            .group_by(UsageEvent.department_id)
        ).all()
        counts = {str(d): int(c) for d, c in rows if d}
        out = []
        for d in depts:
            out.append(
                {
                    "department_id": str(d.id),
                    "name": d.name,
                    "events": counts.get(str(d.id), 0),
                }
            )
        # unassigned bucket
        unassigned = int(
            self.db.scalar(
                select(func.count()).where(
                    UsageEvent.organization_id == organization_id,
                    UsageEvent.created_at >= since,
                    UsageEvent.department_id.is_(None),
                )
            )
            or 0
        )
        out.append(
            {
                "department_id": None,
                "name": "Unassigned / org-wide",
                "events": unassigned,
            }
        )
        out.sort(key=lambda x: x["events"], reverse=True)
        return out

    def storage_breakdown(
        self, *, organization_id: UUID, user_id: UUID
    ) -> dict:
        self._require_admin_or_manager(organization_id, user_id)
        by_status = self.db.execute(
            select(Document.status, func.count(), func.coalesce(func.sum(Document.file_size_bytes), 0))
            .where(
                Document.organization_id == organization_id,
                Document.deleted_at.is_(None),
            )
            .group_by(Document.status)
        ).all()
        by_source = self.db.execute(
            select(
                Document.source_type,
                func.count(),
                func.coalesce(func.sum(Document.file_size_bytes), 0),
            )
            .where(
                Document.organization_id == organization_id,
                Document.deleted_at.is_(None),
            )
            .group_by(Document.source_type)
        ).all()
        total = int(
            self.db.scalar(
                select(func.coalesce(func.sum(Document.file_size_bytes), 0)).where(
                    Document.organization_id == organization_id,
                    Document.deleted_at.is_(None),
                )
            )
            or 0
        )
        return {
            "total_bytes": total,
            "by_status": [
                {"status": s, "count": int(c), "bytes": int(b)} for s, c, b in by_status
            ],
            "by_source": [
                {"source_type": s, "count": int(c), "bytes": int(b)}
                for s, c, b in by_source
            ],
        }

    def search_trends(
        self, *, organization_id: UUID, user_id: UUID, days: int = 30, limit: int = 20
    ) -> list[dict]:
        """Approximate search trends from chat user messages (queries)."""
        self._require_admin_or_manager(organization_id, user_id)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = self.db.scalars(
            select(Message)
            .where(
                Message.organization_id == organization_id,
                Message.role == "user",
                Message.created_at >= since,
            )
            .order_by(Message.created_at.desc())
            .limit(500)
        ).all()
        # simple word frequency on short queries
        freq: dict[str, int] = defaultdict(int)
        for m in rows:
            text = (m.content or "").strip().lower()
            if len(text) < 3 or len(text) > 200:
                continue
            # use first 8 words as phrase key
            words = [w for w in text.replace("?", "").split() if len(w) > 2][:8]
            if not words:
                continue
            key = " ".join(words)
            freq[key] += 1
        ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"query": q, "count": c} for q, c in ranked]

    def top_users(
        self, *, organization_id: UUID, user_id: UUID, days: int = 30, limit: int = 10
    ) -> list[dict]:
        self._require_admin_or_manager(organization_id, user_id)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = self.db.execute(
            select(UsageEvent.user_id, func.count())
            .where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.created_at >= since,
                UsageEvent.user_id.is_not(None),
            )
            .group_by(UsageEvent.user_id)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        out = []
        for uid, count in rows:
            u = self.db.get(User, uid)
            out.append(
                {
                    "user_id": str(uid),
                    "email": u.email if u else None,
                    "full_name": u.full_name if u else None,
                    "events": int(count),
                }
            )
        return out

    def list_audit_logs(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        mem = self.org.get_membership(organization_id, user_id)
        if not role_at_least(mem.role, MembershipRole.ADMIN):
            raise ForbiddenError("Admin role required for audit logs")
        q = select(AuditLog).where(AuditLog.organization_id == organization_id)
        if action:
            q = q.where(AuditLog.action == action)
        total = int(
            self.db.scalar(
                select(func.count()).select_from(q.subquery())
            )
            or 0
        )
        rows = list(
            self.db.scalars(
                q.order_by(AuditLog.created_at.desc()).limit(min(limit, 100)).offset(offset)
            ).all()
        )
        return rows, total
