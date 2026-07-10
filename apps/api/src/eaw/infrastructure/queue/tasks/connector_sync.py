"""Sync runners for Notion and Google Drive connectors."""

from __future__ import annotations

from uuid import UUID


def _base_services():
    from eaw.application.services.audit_service import AuditService
    from eaw.application.services.chat_service import ChatService
    from eaw.application.services.document_service import DocumentService
    from eaw.application.services.gdrive_service import GoogleDriveService
    from eaw.application.services.jira_service import JiraService
    from eaw.application.services.knowledge_service import KnowledgeService
    from eaw.application.services.notion_service import NotionService
    from eaw.application.services.org_service import OrgService
    from eaw.application.services.retrieval_service import RetrievalService
    from eaw.application.services.slack_service import SlackService
    from eaw.core.config import get_settings
    from eaw.infrastructure.db.session import SessionLocal
    from eaw.infrastructure.email.console_email import ConsoleEmailAdapter
    from eaw.infrastructure.embeddings.factory import get_embedding_adapter
    from eaw.infrastructure.llm.factory import get_llm_adapter
    from eaw.infrastructure.storage.factory import get_object_storage
    from eaw.infrastructure.vector.factory import get_vector_store

    db = SessionLocal()
    settings = get_settings()
    email = ConsoleEmailAdapter()
    audit = AuditService(db)
    org = OrgService(db, settings, email, audit)
    knowledge = KnowledgeService(db, org, audit)
    documents = DocumentService(db, org, get_object_storage(), settings, audit)
    retrieval = RetrievalService(
        db, org, get_embedding_adapter(), get_vector_store(), settings
    )
    chat = ChatService(db, org, retrieval, get_llm_adapter(), settings)
    llm = get_llm_adapter()
    notion = NotionService(db, settings, org, knowledge, documents, audit)
    gdrive = GoogleDriveService(db, settings, org, knowledge, documents, audit)
    slack = SlackService(
        db, settings, org, knowledge, documents, audit, llm, chat_service=chat
    )
    jira = JiraService(
        db, settings, org, knowledge, documents, audit, llm, chat_service=chat
    )
    return db, notion, gdrive, slack, jira


def run_notion_sync(job_id: str) -> dict:
    db, notion, _, _, _ = _base_services()
    try:
        job = notion.run_sync_job(UUID(job_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "stats": job.stats,
            "error_message": job.error_message,
        }
    finally:
        db.close()


def run_gdrive_sync(job_id: str) -> dict:
    db, _, gdrive, _, _ = _base_services()
    try:
        job = gdrive.run_sync_job(UUID(job_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "stats": job.stats,
            "error_message": job.error_message,
        }
    finally:
        db.close()


def run_slack_sync(job_id: str) -> dict:
    db, _, _, slack, _ = _base_services()
    try:
        job = slack.run_sync_job(UUID(job_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "stats": job.stats,
            "error_message": job.error_message,
        }
    finally:
        db.close()


def run_jira_sync(job_id: str) -> dict:
    db, _, _, _, jira = _base_services()
    try:
        job = jira.run_sync_job(UUID(job_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "stats": job.stats,
            "error_message": job.error_message,
        }
    finally:
        db.close()
