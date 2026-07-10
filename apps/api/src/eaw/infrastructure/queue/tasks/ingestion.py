"""Celery tasks for document ingestion."""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def _build_ingestion_service():
    from eaw.application.services.ingestion_service import IngestionService
    from eaw.core.config import get_settings
    from eaw.infrastructure.db.session import SessionLocal
    from eaw.infrastructure.embeddings.factory import get_embedding_adapter
    from eaw.infrastructure.storage.factory import get_object_storage
    from eaw.infrastructure.vector.factory import get_vector_store

    db = SessionLocal()
    settings = get_settings()
    svc = IngestionService(
        db=db,
        storage=get_object_storage(),
        embeddings=get_embedding_adapter(),
        vectors=get_vector_store(),
        settings=settings,
    )
    return svc, db


def run_ingest_document(job_id: str) -> dict:
    """Core callable used by Celery task and sync mode."""
    svc, db = _build_ingestion_service()
    try:
        job = svc.run_pipeline(UUID(job_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "stage": job.stage,
            "progress_pct": job.progress_pct,
            "error_message": job.error_message,
            "metrics": job.metrics,
        }
    finally:
        db.close()
