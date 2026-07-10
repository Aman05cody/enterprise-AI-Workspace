"""FastAPI dependencies."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from eaw.application.services.analytics_service import AnalyticsService
from eaw.application.services.audit_service import AuditService
from eaw.application.services.auth_service import AuthService
from eaw.application.services.chat_service import ChatService
from eaw.application.services.document_service import DocumentService
from eaw.application.services.gdrive_service import GoogleDriveService
from eaw.application.services.github_service import GitHubService
from eaw.application.services.ingestion_service import IngestionService
from eaw.application.services.jira_service import JiraService
from eaw.application.services.knowledge_service import KnowledgeService
from eaw.application.services.monitoring_service import MonitoringService
from eaw.application.services.notion_service import NotionService
from eaw.application.services.org_service import OrgService
from eaw.application.services.retrieval_service import RetrievalService
from eaw.application.services.slack_service import SlackService
from eaw.core.config import Settings, get_settings
from eaw.core.security import decode_access_token
from eaw.domain.common.errors import UnauthorizedError
from eaw.infrastructure.db.models.identity import User
from eaw.infrastructure.db.models.tenancy import Membership
from eaw.infrastructure.db.session import get_db
from eaw.infrastructure.email.console_email import ConsoleEmailAdapter
from eaw.infrastructure.embeddings.factory import get_embedding_adapter
from eaw.infrastructure.llm.factory import get_llm_adapter
from eaw.infrastructure.storage.factory import get_object_storage
from eaw.infrastructure.vector.factory import get_vector_store

bearer_scheme = HTTPBearer(auto_error=False)


def get_email_port():
    return ConsoleEmailAdapter()


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(
        db=db,
        settings=settings,
        email=get_email_port(),
        audit=AuditService(db),
    )


def get_org_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OrgService:
    return OrgService(
        db=db,
        settings=settings,
        email=get_email_port(),
        audit=AuditService(db),
    )


def get_knowledge_service(
    db: Annotated[Session, Depends(get_db)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
) -> KnowledgeService:
    return KnowledgeService(db=db, org_service=org_svc, audit=AuditService(db))


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    return DocumentService(
        db=db,
        org_service=org_svc,
        storage=get_object_storage(),
        settings=settings,
        audit=AuditService(db),
    )


def get_ingestion_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionService:
    return IngestionService(
        db=db,
        storage=get_object_storage(),
        embeddings=get_embedding_adapter(),
        vectors=get_vector_store(),
        settings=settings,
    )


def get_retrieval_service(
    db: Annotated[Session, Depends(get_db)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RetrievalService:
    return RetrievalService(
        db=db,
        org_service=org_svc,
        embeddings=get_embedding_adapter(),
        vectors=get_vector_store(),
        settings=settings,
    )


def get_chat_service(
    db: Annotated[Session, Depends(get_db)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    retrieval: Annotated[RetrievalService, Depends(get_retrieval_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService:
    return ChatService(
        db=db,
        org_service=org_svc,
        retrieval=retrieval,
        llm=get_llm_adapter(),
        settings=settings,
    )


def get_github_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    knowledge_svc: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    document_svc: Annotated[DocumentService, Depends(get_document_service)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
) -> GitHubService:
    return GitHubService(
        db=db,
        settings=settings,
        org_service=org_svc,
        knowledge_service=knowledge_svc,
        document_service=document_svc,
        llm=get_llm_adapter(),
        audit=AuditService(db),
        chat_service=chat_svc,
    )


def get_notion_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    knowledge_svc: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    document_svc: Annotated[DocumentService, Depends(get_document_service)],
) -> NotionService:
    return NotionService(
        db=db,
        settings=settings,
        org_service=org_svc,
        knowledge_service=knowledge_svc,
        document_service=document_svc,
        audit=AuditService(db),
    )


def get_drive_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    knowledge_svc: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    document_svc: Annotated[DocumentService, Depends(get_document_service)],
) -> GoogleDriveService:
    return GoogleDriveService(
        db=db,
        settings=settings,
        org_service=org_svc,
        knowledge_service=knowledge_svc,
        document_service=document_svc,
        audit=AuditService(db),
    )


def get_slack_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    knowledge_svc: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    document_svc: Annotated[DocumentService, Depends(get_document_service)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
) -> SlackService:
    return SlackService(
        db=db,
        settings=settings,
        org_service=org_svc,
        knowledge_service=knowledge_svc,
        document_service=document_svc,
        audit=AuditService(db),
        llm=get_llm_adapter(),
        chat_service=chat_svc,
    )


def get_jira_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
    knowledge_svc: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    document_svc: Annotated[DocumentService, Depends(get_document_service)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
) -> JiraService:
    return JiraService(
        db=db,
        settings=settings,
        org_service=org_svc,
        knowledge_service=knowledge_svc,
        document_service=document_svc,
        audit=AuditService(db),
        llm=get_llm_adapter(),
        chat_service=chat_svc,
    )


def get_analytics_service(
    db: Annotated[Session, Depends(get_db)],
    org_svc: Annotated[OrgService, Depends(get_org_service)],
) -> AnalyticsService:
    return AnalyticsService(db=db, org_service=org_svc)


def get_monitoring_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MonitoringService:
    return MonitoringService(db=db, settings=settings)


def get_client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
    return auth.get_user(user_id)


def get_optional_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, auth)
    except UnauthorizedError:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
OrgSvc = Annotated[OrgService, Depends(get_org_service)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
KnowledgeSvc = Annotated[KnowledgeService, Depends(get_knowledge_service)]
DocumentSvc = Annotated[DocumentService, Depends(get_document_service)]
IngestionSvc = Annotated[IngestionService, Depends(get_ingestion_service)]
RetrievalSvc = Annotated[RetrievalService, Depends(get_retrieval_service)]
ChatSvc = Annotated[ChatService, Depends(get_chat_service)]
GitHubSvc = Annotated[GitHubService, Depends(get_github_service)]
NotionSvc = Annotated[NotionService, Depends(get_notion_service)]
DriveSvc = Annotated[GoogleDriveService, Depends(get_drive_service)]
SlackSvc = Annotated[SlackService, Depends(get_slack_service)]
JiraSvc = Annotated[JiraService, Depends(get_jira_service)]
AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]
MonitoringSvc = Annotated[MonitoringService, Depends(get_monitoring_service)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def require_org_membership(
    org_id: UUID,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> Membership:
    return org_svc.get_membership(org_id, user.id)


def get_active_org_header(
    x_organization_id: Annotated[Optional[str], Header(alias="X-Organization-Id")] = None,
) -> Optional[UUID]:
    if not x_organization_id:
        return None
    try:
        return UUID(x_organization_id)
    except ValueError as exc:
        raise UnauthorizedError("Invalid X-Organization-Id header") from exc
