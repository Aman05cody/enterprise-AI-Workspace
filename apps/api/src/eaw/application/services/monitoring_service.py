"""Runtime monitoring snapshot for operators."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from eaw import __version__
from eaw.core.config import Settings
from eaw.infrastructure.db.models.connectors import ConnectorSyncJob
from eaw.infrastructure.db.models.ingestion import IngestionJob
from eaw.infrastructure.db.models.knowledge import Document


class MonitoringService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def snapshot(self) -> dict[str, Any]:
        checks: dict[str, str] = {}
        try:
            self.db.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["postgres"] = f"error: {exc}"

        # Redis optional probe
        try:
            import redis

            r = redis.from_url(self.settings.redis_url, socket_connect_timeout=1)
            r.ping()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"unavailable: {exc}"

        # Qdrant optional
        try:
            import httpx

            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self.settings.qdrant_url.rstrip('/')}/readyz")
            checks["qdrant"] = "ok" if resp.status_code < 500 else f"status {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            checks["qdrant"] = f"unavailable: {exc}"

        pending_docs = int(
            self.db.scalar(
                select(func.count()).where(Document.status == "pending")
            )
            or 0
        )
        processing_docs = int(
            self.db.scalar(
                select(func.count()).where(Document.status == "processing")
            )
            or 0
        )
        failed_docs = int(
            self.db.scalar(select(func.count()).where(Document.status == "failed"))
            or 0
        )
        queued_jobs = int(
            self.db.scalar(
                select(func.count()).where(IngestionJob.status.in_(["queued", "running"]))
            )
            or 0
        )
        sync_running = int(
            self.db.scalar(
                select(func.count()).where(
                    ConnectorSyncJob.status.in_(["queued", "running"])
                )
            )
            or 0
        )

        overall = "ok" if checks.get("postgres") == "ok" else "degraded"
        return {
            "status": overall,
            "version": __version__,
            "env": self.settings.app_env,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "queues": {
                "documents_pending": pending_docs,
                "documents_processing": processing_docs,
                "documents_failed": failed_docs,
                "ingestion_jobs_active": queued_jobs,
                "connector_sync_active": sync_running,
            },
            "config": {
                "ingestion_mode": self.settings.ingestion_mode,
                "embedding_provider": self.settings.embedding_provider,
                "vector_store_backend": self.settings.vector_store_backend,
                "llm_provider": self.settings.llm_provider,
            },
        }
