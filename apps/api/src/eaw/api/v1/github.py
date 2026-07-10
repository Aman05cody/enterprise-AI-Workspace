"""GitHub connector & intelligence routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from eaw.api.deps import CurrentUser, GitHubSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.github import (
    ConnectorOut,
    ConnectorResourceOut,
    ExplainRequest,
    GenerateRequest,
    GitHubConnectRequest,
    PRReviewRequest,
    RepoChatRequest,
    ResourceSelectionRequest,
    SyncJobOut,
    SyncRequest,
)

router = APIRouter(prefix="/github", tags=["github"])


def _connector_out(c) -> ConnectorOut:
    # strip secrets from config if any
    cfg = dict(c.config or {})
    return ConnectorOut(
        id=c.id,
        organization_id=c.organization_id,
        type=c.type,
        status=c.status,
        display_name=c.display_name,
        config=cfg,
        last_synced_at=c.last_synced_at,
        created_at=c.created_at,
    )


def _resource_out(r) -> ConnectorResourceOut:
    return ConnectorResourceOut(
        id=r.id,
        connector_id=r.connector_id,
        external_id=r.external_id,
        name=r.name,
        resource_type=r.resource_type,
        sync_enabled=r.sync_enabled,
        metadata=r.metadata_ or {},
        knowledge_base_id=r.knowledge_base_id,
        last_synced_at=r.last_synced_at,
    )


@router.post("/connect", response_model=DataResponse[ConnectorOut], status_code=201)
def connect(
    body: GitHubConnectRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[ConnectorOut]:
    c = gh.connect_with_pat(
        organization_id=body.organization_id,
        user_id=user.id,
        personal_access_token=body.personal_access_token,
        display_name=body.display_name,
    )
    return DataResponse(
        data=_connector_out(c),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/connectors", response_model=DataResponse[list[ConnectorOut]])
def list_connectors(
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
    organization_id: UUID = Query(...),
) -> DataResponse[list[ConnectorOut]]:
    rows = gh.list_connectors(organization_id=organization_id, user_id=user.id)
    return DataResponse(
        data=[_connector_out(c) for c in rows],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(rows)
        ),
    )


@router.delete(
    "/connectors/{connector_id}", response_model=MessageResponse
)
def disconnect(
    connector_id: UUID,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> MessageResponse:
    gh.disconnect(connector_id=connector_id, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/connectors/{connector_id}/refresh-repos",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def refresh_repos(
    connector_id: UUID,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = gh.refresh_repo_catalog(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(rows)
        ),
    )


@router.get(
    "/connectors/{connector_id}/repos",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def list_repos(
    connector_id: UUID,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = gh.list_resources(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(rows)
        ),
    )


@router.put(
    "/connectors/{connector_id}/repos/selection",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def select_repos(
    connector_id: UUID,
    body: ResourceSelectionRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = gh.set_resource_selection(
        connector_id=connector_id,
        user_id=user.id,
        resource_ids=body.resource_ids,
    )
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(rows)
        ),
    )


@router.post(
    "/connectors/{connector_id}/sync",
    response_model=DataResponse[SyncJobOut],
    status_code=202,
)
def sync(
    connector_id: UUID,
    body: SyncRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[SyncJobOut]:
    job = gh.sync_connector(
        connector_id=connector_id,
        user_id=user.id,
        resource_id=body.resource_id,
    )
    # re-load after sync may complete
    job = gh.db.get(type(job), job.id) or job
    return DataResponse(
        data=SyncJobOut.model_validate(job),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/pulls/review", response_model=DataResponse[dict[str, Any]])
def review_pr(
    body: PRReviewRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[dict[str, Any]]:
    data = gh.review_pull_request(
        connector_id=body.connector_id,
        user_id=user.id,
        owner=body.owner,
        repo=body.repo,
        pull_number=body.pull_number,
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/explain", response_model=DataResponse[dict[str, Any]])
def explain(
    body: ExplainRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[dict[str, Any]]:
    data = gh.explain_code(
        connector_id=body.connector_id,
        user_id=user.id,
        owner=body.owner,
        repo=body.repo,
        path=body.path,
        ref=body.ref,
        focus=body.focus,
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/generate-docs", response_model=DataResponse[dict[str, Any]])
def generate_docs(
    body: GenerateRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[dict[str, Any]]:
    data = gh.generate_docs(
        connector_id=body.connector_id,
        user_id=user.id,
        owner=body.owner,
        repo=body.repo,
        path=body.path,
        ref=body.ref,
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/generate-tests", response_model=DataResponse[dict[str, Any]])
def generate_tests(
    body: GenerateRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[dict[str, Any]]:
    data = gh.generate_tests(
        connector_id=body.connector_id,
        user_id=user.id,
        owner=body.owner,
        repo=body.repo,
        path=body.path,
        ref=body.ref,
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/repos/{resource_id}/architecture",
    response_model=DataResponse[dict[str, Any]],
)
def architecture(
    resource_id: UUID,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[dict[str, Any]]:
    data = gh.explain_architecture(resource_id=resource_id, user_id=user.id)
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/repos/{resource_id}/chat",
    response_model=DataResponse[dict[str, Any]],
)
def repo_chat(
    resource_id: UUID,
    body: RepoChatRequest,
    request: Request,
    user: CurrentUser,
    gh: GitHubSvc,
) -> DataResponse[dict[str, Any]]:
    data = gh.chat_with_repo(
        resource_id=resource_id,
        user_id=user.id,
        question=body.question,
        conversation_id=body.conversation_id,
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )
