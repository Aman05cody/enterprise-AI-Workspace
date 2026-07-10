"""Notion connector routes."""

from uuid import UUID

from fastapi import APIRouter, Query, Request

from eaw.api.deps import CurrentUser, NotionSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.connectors import (
    ConnectorOut,
    ConnectorResourceOut,
    NotionConnectRequest,
    ResourceSelectionRequest,
    SyncJobOut,
    SyncRequest,
)

router = APIRouter(prefix="/notion", tags=["notion"])


def _connector_out(c) -> ConnectorOut:
    cfg = dict(c.config or {})
    # never leak secrets from config
    cfg.pop("client_secret", None)
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
    body: NotionConnectRequest,
    request: Request,
    user: CurrentUser,
    svc: NotionSvc,
) -> DataResponse[ConnectorOut]:
    c = svc.connect(
        organization_id=body.organization_id,
        user_id=user.id,
        integration_token=body.integration_token,
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
    svc: NotionSvc,
    organization_id: UUID = Query(...),
) -> DataResponse[list[ConnectorOut]]:
    rows = svc.list_connectors(organization_id=organization_id, user_id=user.id)
    return DataResponse(
        data=[_connector_out(c) for c in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.delete("/connectors/{connector_id}", response_model=MessageResponse)
def disconnect(
    connector_id: UUID, request: Request, user: CurrentUser, svc: NotionSvc
) -> MessageResponse:
    svc.disconnect(connector_id=connector_id, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/connectors/{connector_id}/refresh-pages",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def refresh_pages(
    connector_id: UUID, request: Request, user: CurrentUser, svc: NotionSvc
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.refresh_catalog(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.get(
    "/connectors/{connector_id}/pages",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def list_pages(
    connector_id: UUID, request: Request, user: CurrentUser, svc: NotionSvc
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.list_resources(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.put(
    "/connectors/{connector_id}/pages/selection",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def select_pages(
    connector_id: UUID,
    body: ResourceSelectionRequest,
    request: Request,
    user: CurrentUser,
    svc: NotionSvc,
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.set_selection(
        connector_id=connector_id, user_id=user.id, resource_ids=body.resource_ids
    )
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
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
    svc: NotionSvc,
) -> DataResponse[SyncJobOut]:
    job = svc.sync(
        connector_id=connector_id, user_id=user.id, resource_id=body.resource_id
    )
    job = svc.db.get(type(job), job.id) or job
    return DataResponse(
        data=SyncJobOut.model_validate(job),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )
