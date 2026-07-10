"""Document upload, versioning, search, and lifecycle."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from eaw.application.ports.object_storage import ObjectStoragePort
from eaw.application.services.audit_service import AuditService
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import DocumentStatus, MembershipRole, SourceType, StorageBackend
from eaw.domain.common.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)
from eaw.domain.tenancy.policies import (
    can_delete_any_document,
    can_read_knowledge,
    can_upload_documents,
    require_role,
)
from eaw.infrastructure.db.models.knowledge import Document, DocumentVersion, KnowledgeBase
from eaw.infrastructure.storage.file_validation import extract_text_preview, validate_upload


class DocumentService:
    def _enqueue_ingest(self, document_id: UUID) -> None:
        """Create ingestion job and run pipeline (sync or Celery)."""
        from eaw.application.services.ingestion_service import IngestionService
        from eaw.infrastructure.embeddings.factory import get_embedding_adapter
        from eaw.infrastructure.queue.enqueue import enqueue_ingestion_job
        from eaw.infrastructure.vector.factory import get_vector_store

        ing = IngestionService(
            db=self.db,
            storage=self.storage,
            embeddings=get_embedding_adapter(),
            vectors=get_vector_store(),
            settings=self.settings,
        )
        job = ing.create_job(document_id)
        task_id = enqueue_ingestion_job(job.id)
        if task_id:
            job.celery_task_id = task_id
            self.db.commit()
    def __init__(
        self,
        db: Session,
        org_service: OrgService,
        storage: ObjectStoragePort,
        settings: Settings,
        audit: AuditService,
    ) -> None:
        self.db = db
        self.org = org_service
        self.storage = storage
        self.settings = settings
        self.audit = audit

    def _kb(self, kb_id: UUID) -> KnowledgeBase:
        kb = self.db.get(KnowledgeBase, kb_id)
        if kb is None or kb.deleted_at is not None:
            raise NotFoundError("Knowledge base not found")
        return kb

    def _doc(self, document_id: UUID) -> Document:
        doc = self.db.get(Document, document_id)
        if doc is None or doc.deleted_at is not None:
            raise NotFoundError("Document not found")
        return doc

    def _storage_backend_name(self) -> str:
        return (
            StorageBackend.S3.value
            if (self.settings.storage_backend or "local").lower() == "s3"
            else StorageBackend.LOCAL.value
        )

    def _storage_key(
        self,
        *,
        org_id: UUID,
        kb_id: UUID,
        doc_id: UUID,
        version: int,
        filename: str,
    ) -> str:
        return f"{org_id}/{kb_id}/{doc_id}/v{version}/{filename}"

    def upload(
        self,
        *,
        kb_id: UUID,
        user_id: UUID,
        filename: str,
        content_type: str | None,
        data: bytes,
        title: Optional[str] = None,
    ) -> Document:
        kb = self._kb(kb_id)
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_upload_documents(mem.role):
            raise ForbiddenError("Insufficient permissions to upload documents")

        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        validated = validate_upload(
            filename=filename,
            content_type=content_type,
            data=data,
            max_bytes=max_bytes,
        )

        # Duplicate checksum in same KB (active)
        dup = self.db.scalar(
            select(Document).where(
                Document.knowledge_base_id == kb_id,
                Document.checksum_sha256 == validated.checksum_sha256,
                Document.deleted_at.is_(None),
            )
        )
        if dup:
            raise ConflictError(
                "An identical document already exists in this knowledge base",
                details={"existing_document_id": str(dup.id)},
            )

        doc_id = uuid4()
        version = 1
        key = self._storage_key(
            org_id=kb.organization_id,
            kb_id=kb.id,
            doc_id=doc_id,
            version=version,
            filename=validated.filename,
        )
        self.storage.put_object(
            key=key,
            body=validated.data,
            content_type=validated.content_type,
            content_length=validated.size_bytes,
        )

        preview = extract_text_preview(validated.data, validated.extension)
        # Phase 3: stored successfully; indexing deferred to Phase 4 → pending
        status = DocumentStatus.PENDING.value

        doc = Document(
            id=doc_id,
            organization_id=kb.organization_id,
            knowledge_base_id=kb.id,
            title=(title or validated.filename).strip()[:500],
            original_filename=validated.filename,
            content_type=validated.content_type,
            file_size_bytes=validated.size_bytes,
            checksum_sha256=validated.checksum_sha256,
            storage_backend=self._storage_backend_name(),
            storage_key=key,
            status=status,
            source_type=SourceType.UPLOAD.value,
            current_version=version,
            preview_text=preview,
            ai_tags=[],
            uploaded_by=user_id,
        )
        self.db.add(doc)
        self.db.add(
            DocumentVersion(
                document_id=doc_id,
                organization_id=kb.organization_id,
                version_number=version,
                storage_key=key,
                checksum_sha256=validated.checksum_sha256,
                content_type=validated.content_type,
                file_size_bytes=validated.size_bytes,
                original_filename=validated.filename,
                created_by=user_id,
                created_at=datetime.now(timezone.utc),
            )
        )
        self.audit.log(
            action="document.uploaded",
            actor_user_id=user_id,
            organization_id=kb.organization_id,
            resource_type="document",
            resource_id=doc_id,
            metadata={
                "filename": validated.filename,
                "size": validated.size_bytes,
                "kb_id": str(kb_id),
            },
        )
        try:
            from eaw.application.services.usage_service import UsageService

            UsageService(self.db).track(
                organization_id=kb.organization_id,
                user_id=user_id,
                event_type="upload",
                metadata={
                    "document_id": str(doc_id),
                    "bytes": validated.size_bytes,
                    "kb_id": str(kb_id),
                },
            )
        except Exception:  # noqa: BLE001
            pass
        self.db.commit()
        self.db.refresh(doc)
        self._enqueue_ingest(doc.id)
        self.db.refresh(doc)
        return doc

    def ingest_text(
        self,
        *,
        kb_id: UUID,
        user_id: UUID,
        title: str,
        text: str,
        source_type: str = SourceType.GITHUB.value,
        source_path: Optional[str] = None,
        skip_duplicate: bool = True,
    ) -> Optional[Document]:
        """
        Ingest plain-text content from a connector (GitHub files, etc.).
        Stores as .md for pipeline compatibility.
        """
        kb = self._kb(kb_id)
        content = (text or "").strip()
        if not content:
            return None

        data = content.encode("utf-8")
        checksum = hashlib.sha256(data).hexdigest()
        if skip_duplicate:
            dup = self.db.scalar(
                select(Document).where(
                    Document.knowledge_base_id == kb_id,
                    Document.checksum_sha256 == checksum,
                    Document.deleted_at.is_(None),
                )
            )
            if dup:
                return dup

        safe = re.sub(r"[^\w.\-]+", "_", (source_path or title))[:180] or "file"
        if not safe.endswith((".md", ".txt")):
            safe = f"{safe}.md"

        doc_id = uuid4()
        version = 1
        key = self._storage_key(
            org_id=kb.organization_id,
            kb_id=kb.id,
            doc_id=doc_id,
            version=version,
            filename=safe,
        )
        self.storage.put_object(
            key=key,
            body=data,
            content_type="text/markdown",
            content_length=len(data),
        )
        doc = Document(
            id=doc_id,
            organization_id=kb.organization_id,
            knowledge_base_id=kb.id,
            title=title.strip()[:500],
            original_filename=safe,
            content_type="text/markdown",
            file_size_bytes=len(data),
            checksum_sha256=checksum,
            storage_backend=self._storage_backend_name(),
            storage_key=key,
            status=DocumentStatus.PENDING.value,
            source_type=source_type,
            current_version=version,
            preview_text=content[:4000],
            ai_tags=["github"] if source_type == SourceType.GITHUB.value else [],
            uploaded_by=user_id,
        )
        self.db.add(doc)
        self.db.add(
            DocumentVersion(
                document_id=doc_id,
                organization_id=kb.organization_id,
                version_number=version,
                storage_key=key,
                checksum_sha256=checksum,
                content_type="text/markdown",
                file_size_bytes=len(data),
                original_filename=safe,
                created_by=user_id,
                created_at=datetime.now(timezone.utc),
            )
        )
        try:
            from eaw.application.services.usage_service import UsageService

            UsageService(self.db).track(
                organization_id=kb.organization_id,
                user_id=user_id,
                event_type="ingest_source",
                metadata={
                    "document_id": str(doc_id),
                    "source_type": source_type,
                    "bytes": len(data),
                },
            )
        except Exception:  # noqa: BLE001
            pass
        self.db.commit()
        self.db.refresh(doc)
        self._enqueue_ingest(doc.id)
        self.db.refresh(doc)
        return doc

    def upload_new_version(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> Document:
        doc = self._doc(document_id)
        mem = self.org.get_membership(doc.organization_id, user_id)
        if not can_upload_documents(mem.role):
            raise ForbiddenError("Insufficient permissions to upload document versions")

        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        validated = validate_upload(
            filename=filename,
            content_type=content_type,
            data=data,
            max_bytes=max_bytes,
        )

        new_version = doc.current_version + 1
        key = self._storage_key(
            org_id=doc.organization_id,
            kb_id=doc.knowledge_base_id,
            doc_id=doc.id,
            version=new_version,
            filename=validated.filename,
        )
        self.storage.put_object(
            key=key,
            body=validated.data,
            content_type=validated.content_type,
            content_length=validated.size_bytes,
        )
        preview = extract_text_preview(validated.data, validated.extension)

        doc.current_version = new_version
        doc.original_filename = validated.filename
        doc.content_type = validated.content_type
        doc.file_size_bytes = validated.size_bytes
        doc.checksum_sha256 = validated.checksum_sha256
        doc.storage_key = key
        doc.storage_backend = self._storage_backend_name()
        doc.preview_text = preview
        doc.status = DocumentStatus.PENDING.value
        doc.error_message = None
        doc.chunk_count = 0
        doc.processed_at = None

        self.db.add(
            DocumentVersion(
                document_id=doc.id,
                organization_id=doc.organization_id,
                version_number=new_version,
                storage_key=key,
                checksum_sha256=validated.checksum_sha256,
                content_type=validated.content_type,
                file_size_bytes=validated.size_bytes,
                original_filename=validated.filename,
                created_by=user_id,
                created_at=datetime.now(timezone.utc),
            )
        )
        self.audit.log(
            action="document.version_uploaded",
            actor_user_id=user_id,
            organization_id=doc.organization_id,
            resource_type="document",
            resource_id=doc.id,
            metadata={"version": new_version},
        )
        self.db.commit()
        self.db.refresh(doc)
        self._enqueue_ingest(doc.id)
        self.db.refresh(doc)
        return doc

    def list_documents(
        self,
        *,
        kb_id: UUID,
        user_id: UUID,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        kb = self._kb(kb_id)
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="list documents")

        stmt = select(Document).where(
            Document.knowledge_base_id == kb_id,
            Document.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(Document.status == status)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Document.title.ilike(like),
                    Document.original_filename.ilike(like),
                    Document.preview_text.ilike(like),
                )
            )

        from sqlalchemy import func

        total = int(
            self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        )
        docs = list(
            self.db.scalars(
                stmt.order_by(Document.created_at.desc()).limit(min(limit, 100)).offset(offset)
            ).all()
        )
        return docs, total

    def get_document(self, *, document_id: UUID, user_id: UUID) -> Document:
        doc = self._doc(document_id)
        mem = self.org.get_membership(doc.organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="view document")
        return doc

    def get_preview(self, *, document_id: UUID, user_id: UUID) -> dict:
        doc = self.get_document(document_id=document_id, user_id=user_id)
        return {
            "document_id": doc.id,
            "title": doc.title,
            "content_type": doc.content_type,
            "preview_text": doc.preview_text,
            "has_preview": bool(doc.preview_text),
            "status": doc.status,
            "current_version": doc.current_version,
        }

    def list_versions(self, *, document_id: UUID, user_id: UUID) -> list[DocumentVersion]:
        doc = self.get_document(document_id=document_id, user_id=user_id)
        return list(
            self.db.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == doc.id)
                .order_by(DocumentVersion.version_number.desc())
            ).all()
        )

    def soft_delete(self, *, document_id: UUID, user_id: UUID) -> None:
        doc = self._doc(document_id)
        mem = self.org.get_membership(doc.organization_id, user_id)
        is_owner_upload = doc.uploaded_by == user_id
        if not (
            can_delete_any_document(mem.role)
            or (is_owner_upload and can_upload_documents(mem.role))
        ):
            raise ForbiddenError("Insufficient permissions to delete document")

        doc.deleted_at = datetime.now(timezone.utc)
        doc.status = DocumentStatus.DELETED.value
        # Best-effort remove current object (versions retained for audit optional — soft only)
        try:
            self.storage.delete_object(key=doc.storage_key)
        except Exception:  # noqa: BLE001
            pass
        try:
            from eaw.infrastructure.vector.factory import get_vector_store

            get_vector_store().delete_by_document(
                organization_id=doc.organization_id, document_id=doc.id
            )
        except Exception:  # noqa: BLE001
            pass

        self.audit.log(
            action="document.deleted",
            actor_user_id=user_id,
            organization_id=doc.organization_id,
            resource_type="document",
            resource_id=doc.id,
        )
        self.db.commit()

    def download(self, *, document_id: UUID, user_id: UUID) -> tuple[Document, bytes]:
        doc = self.get_document(document_id=document_id, user_id=user_id)
        data = self.storage.get_object(key=doc.storage_key)
        return doc, data

    def search_workspace(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        query: str,
        knowledge_base_id: Optional[UUID] = None,
        limit: int = 20,
    ) -> list[Document]:
        mem = self.org.get_membership(organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="search documents")
        if not query or not query.strip():
            raise ValidationAppError("Query is required")

        like = f"%{query.strip()}%"
        stmt = select(Document).where(
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
            or_(
                Document.title.ilike(like),
                Document.original_filename.ilike(like),
                Document.preview_text.ilike(like),
            ),
        )
        if knowledge_base_id:
            stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)

        return list(
            self.db.scalars(
                stmt.order_by(Document.updated_at.desc()).limit(min(limit, 50))
            ).all()
        )
