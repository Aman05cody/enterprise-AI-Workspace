"""Celery/sync runner for GitHub connector sync jobs."""

from __future__ import annotations

from uuid import UUID


def run_github_sync(job_id: str) -> dict:
    from eaw.application.services.audit_service import AuditService
    from eaw.application.services.chat_service import ChatService
    from eaw.application.services.document_service import DocumentService
    from eaw.application.services.github_service import GitHubService
    from eaw.application.services.knowledge_service import KnowledgeService
    from eaw.application.services.org_service import OrgService
    from eaw.application.services.retrieval_service import RetrievalService
    from eaw.core.config import get_settings
    from eaw.infrastructure.db.session import SessionLocal
    from eaw.infrastructure.email.console_email import ConsoleEmailAdapter
    from eaw.infrastructure.embeddings.factory import get_embedding_adapter
    from eaw.infrastructure.llm.factory import get_llm_adapter
    from eaw.infrastructure.storage.factory import get_object_storage
    from eaw.infrastructure.vector.factory import get_vector_store

    db = SessionLocal()
    settings = get_settings()
    try:
        email = ConsoleEmailAdapter()
        audit = AuditService(db)
        org = OrgService(db, settings, email, audit)
        knowledge = KnowledgeService(db, org, audit)
        documents = DocumentService(
            db, org, get_object_storage(), settings, audit
        )
        retrieval = RetrievalService(
            db, org, get_embedding_adapter(), get_vector_store(), settings
        )
        chat = ChatService(db, org, retrieval, get_llm_adapter(), settings)
        gh = GitHubService(
            db=db,
            settings=settings,
            org_service=org,
            knowledge_service=knowledge,
            document_service=documents,
            llm=get_llm_adapter(),
            audit=audit,
            chat_service=chat,
        )
        job = gh.run_sync_job(UUID(job_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "stats": job.stats,
            "error_message": job.error_message,
        }
    finally:
        db.close()
