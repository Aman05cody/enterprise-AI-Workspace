"""Document ingestion pipeline orchestration."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from eaw.application.ports.embeddings import EmbeddingPort
from eaw.application.ports.object_storage import ObjectStoragePort
from eaw.application.ports.vector_store import VectorPoint, VectorStorePort
from eaw.core.config import Settings
from eaw.domain.common.enums import (
    DocumentStatus,
    IngestionJobStatus,
    IngestionStage,
    MembershipRole,
)
from eaw.domain.common.errors import NotFoundError
from eaw.domain.tenancy.policies import require_role, can_manage_knowledge_bases
from eaw.infrastructure.db.models.ingestion import DocumentChunk, IngestionJob
from eaw.infrastructure.db.models.knowledge import Document, KnowledgeBase
from eaw.infrastructure.rag.chunking import chunk_text
from eaw.infrastructure.rag.text_extraction import extract_full_text

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        db: Session,
        storage: ObjectStoragePort,
        embeddings: EmbeddingPort,
        vectors: VectorStorePort,
        settings: Settings,
    ) -> None:
        self.db = db
        self.storage = storage
        self.embeddings = embeddings
        self.vectors = vectors
        self.settings = settings

    def create_job(self, document_id: UUID) -> IngestionJob:
        doc = self.db.get(Document, document_id)
        if doc is None or doc.deleted_at is not None:
            raise NotFoundError("Document not found")

        now = datetime.now(timezone.utc)
        job = IngestionJob(
            id=uuid4(),
            organization_id=doc.organization_id,
            document_id=doc.id,
            status=IngestionJobStatus.QUEUED.value,
            stage=IngestionStage.QUEUED.value,
            progress_pct=0,
            attempt=1,
            metrics={},
            created_at=now,
            updated_at=now,
        )
        self.db.add(job)
        doc.status = DocumentStatus.PENDING.value
        doc.error_message = None
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self, document_id: UUID) -> list[IngestionJob]:
        return list(
            self.db.scalars(
                select(IngestionJob)
                .where(IngestionJob.document_id == document_id)
                .order_by(IngestionJob.created_at.desc())
            ).all()
        )

    def get_job(self, job_id: UUID) -> IngestionJob:
        job = self.db.get(IngestionJob, job_id)
        if job is None:
            raise NotFoundError("Ingestion job not found")
        return job

    def reprocess(self, *, document_id: UUID, user_id: UUID) -> IngestionJob:
        from eaw.application.services.org_service import OrgService
        from eaw.infrastructure.email.console_email import ConsoleEmailAdapter
        from eaw.application.services.audit_service import AuditService

        doc = self.db.get(Document, document_id)
        if doc is None or doc.deleted_at is not None:
            raise NotFoundError("Document not found")

        org_svc = OrgService(
            self.db, self.settings, ConsoleEmailAdapter(), AuditService(self.db)
        )
        mem = org_svc.get_membership(doc.organization_id, user_id)
        if not can_manage_knowledge_bases(mem.role):
            require_role(mem.role, MembershipRole.MANAGER, action="reprocess documents")

        return self.create_job(document_id)

    def _update_job(
        self,
        job: IngestionJob,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        metrics: Optional[dict] = None,
    ) -> None:
        if status:
            job.status = status
        if stage:
            job.stage = stage
        if progress is not None:
            job.progress_pct = progress
        if error is not None:
            job.error_message = error
        if metrics:
            job.metrics = {**(job.metrics or {}), **metrics}
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def run_pipeline(self, job_id: UUID) -> IngestionJob:
        """Execute extract → clean → chunk → embed → index for a job."""
        job = self.get_job(job_id)
        doc = self.db.get(Document, job.document_id)
        if doc is None or doc.deleted_at is not None:
            self._update_job(
                job,
                status=IngestionJobStatus.FAILED.value,
                error="Document missing",
                progress=100,
            )
            return job

        kb = self.db.get(KnowledgeBase, doc.knowledge_base_id)
        started = time.perf_counter()
        job.started_at = datetime.now(timezone.utc)
        job.attempt = (job.attempt or 0) + (
            0 if job.status == IngestionJobStatus.QUEUED.value else 1
        )
        if job.attempt < 1:
            job.attempt = 1
        self._update_job(
            job,
            status=IngestionJobStatus.RUNNING.value,
            stage=IngestionStage.EXTRACT.value,
            progress=5,
        )
        doc.status = DocumentStatus.PROCESSING.value
        self.db.commit()

        try:
            # Extract
            raw = self.storage.get_object(key=doc.storage_key)
            text = extract_full_text(
                data=raw,
                filename=doc.original_filename,
                content_type=doc.content_type,
            )
            self._update_job(
                job,
                stage=IngestionStage.CLEAN.value,
                progress=20,
                metrics={"chars_extracted": len(text)},
            )

            # Chunk
            settings = (kb.settings if kb else {}) or {}
            chunk_size = int(settings.get("chunk_size") or self.settings.chunk_size)
            chunk_overlap = int(
                settings.get("chunk_overlap") or self.settings.chunk_overlap
            )
            chunks = chunk_text(
                text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            if not chunks:
                raise ValueError("No text chunks produced from document")

            self._update_job(
                job,
                stage=IngestionStage.CHUNK.value,
                progress=40,
                metrics={"chunk_count": len(chunks)},
            )

            # Replace prior chunks + vectors (idempotent reprocess)
            self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            self.db.commit()
            try:
                self.vectors.delete_by_document(
                    organization_id=doc.organization_id, document_id=doc.id
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Vector delete skipped/failed: %s", exc)

            # Embed
            self._update_job(
                job, stage=IngestionStage.EMBED.value, progress=55
            )
            texts = [c.content for c in chunks]
            vectors = self.embeddings.embed_documents(texts)
            if len(vectors) != len(chunks):
                raise ValueError("Embedding count mismatch")

            dim = len(vectors[0]) if vectors else self.embeddings.dimensions
            self.vectors.ensure_collection(vector_size=dim)

            # Persist chunks + index
            self._update_job(
                job, stage=IngestionStage.INDEX.value, progress=75
            )
            now = datetime.now(timezone.utc)
            points: list[VectorPoint] = []
            for ch, vec in zip(chunks, vectors):
                chunk_id = uuid4()
                point_id = str(chunk_id)
                self.db.add(
                    DocumentChunk(
                        id=chunk_id,
                        organization_id=doc.organization_id,
                        knowledge_base_id=doc.knowledge_base_id,
                        document_id=doc.id,
                        version_number=doc.current_version,
                        chunk_index=ch.index,
                        content=ch.content,
                        token_count=ch.token_count,
                        metadata_={
                            **ch.metadata,
                            "title": doc.title,
                            "filename": doc.original_filename,
                        },
                        vector_point_id=point_id,
                        created_at=now,
                    )
                )
                points.append(
                    VectorPoint(
                        id=point_id,
                        vector=vec,
                        payload={
                            "organization_id": str(doc.organization_id),
                            "knowledge_base_id": str(doc.knowledge_base_id),
                            "document_id": str(doc.id),
                            "chunk_id": point_id,
                            "chunk_index": ch.index,
                            "version_number": doc.current_version,
                            "title": doc.title,
                            "content_preview": ch.content[:500],
                            "source_type": doc.source_type,
                        },
                    )
                )
            self.db.commit()

            # Upsert in batches
            batch = 64
            for i in range(0, len(points), batch):
                self.vectors.upsert(points[i : i + batch])

            # Finalize
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            doc.status = DocumentStatus.READY.value
            doc.chunk_count = len(chunks)
            doc.embedding_model = self.embeddings.model_name
            doc.token_count = sum(c.token_count for c in chunks)
            doc.processed_at = datetime.now(timezone.utc)
            doc.error_message = None
            if not doc.preview_text and text:
                doc.preview_text = text[:4000]
            try:
                from eaw.application.services.usage_service import UsageService

                UsageService(self.db).track(
                    organization_id=doc.organization_id,
                    user_id=doc.uploaded_by,
                    event_type="embed",
                    model=self.embeddings.model_name,
                    metadata={
                        "document_id": str(doc.id),
                        "chunks": len(chunks),
                        "duration_ms": elapsed_ms,
                    },
                )
            except Exception:  # noqa: BLE001
                pass

            job.finished_at = datetime.now(timezone.utc)
            self._update_job(
                job,
                status=IngestionJobStatus.SUCCEEDED.value,
                stage=IngestionStage.FINALIZE.value,
                progress=100,
                metrics={
                    "chunk_count": len(chunks),
                    "embedding_model": self.embeddings.model_name,
                    "vector_dim": dim,
                    "duration_ms": elapsed_ms,
                },
            )
            self.db.commit()
            self.db.refresh(job)
            logger.info(
                "Ingestion succeeded doc=%s chunks=%s ms=%s",
                doc.id,
                len(chunks),
                elapsed_ms,
            )
            return job

        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestion failed job=%s", job_id)
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            self._update_job(
                job,
                status=IngestionJobStatus.FAILED.value,
                error=str(exc)[:2000],
                progress=100,
            )
            self.db.commit()
            self.db.refresh(job)
            return job
