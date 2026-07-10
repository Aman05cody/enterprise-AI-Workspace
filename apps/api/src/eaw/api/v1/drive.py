"""Google Drive connector routes."""

from uuid import UUID

from fastapi import APIRouter, Query, Request

from eaw.api.deps import CurrentUser, DriveSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.connectors import (
    ConnectorOut,
    ConnectorResourceOut,
    DriveConnectRequest,
    ResourceSelectionRequest,
    SyncJobOut,
    SyncRequest,
)

router = APIRouter(prefix="/drive", tags=["drive"])


def _connector_out(c) -> ConnectorOut:
    cfg = dict(c.config or {})
    cfg.pop("client_secret", None)
    return ConnectorOut(
        id=c.id,
        organization_id=c.organization_id,
        type=c.type,
        status=c.status,
        display_name=c.display_name,
        config={k: v for k, v in cfg.items() if k != "client_secret"},
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
    body: DriveConnectRequest,
    request: Request,
    user: CurrentUser,
    svc: DriveSvc,
) -> DataResponse[ConnectorOut]:
    c = svc.connect(
        organization_id=body.organization_id,
        user_id=user.id,
        access_token=body.access_token,
        refresh_token=body.refresh_token,
        client_id=body.client_id,
        client_secret=body.client_secret,
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
    svc: DriveSvc,
    organization_id: UUID = Query(...),
) -> DataResponse[list[ConnectorOut]]:
    rows = svc.list_connectors(organization_id=organization_id, user_id=user.id)
    return DataResponse(
        data=[_connector_out(c) for c in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.delete("/connectors/{connector_id}", response_model=MessageResponse)
def disconnect(
    connector_id: UUID, request: Request, user: CurrentUser, svc: DriveSvc
) -> MessageResponse:
    svc.disconnect(connector_id=connector_id, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/connectors/{connector_id}/refresh-folders",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def refresh_folders(
    connector_id: UUID, request: Request, user: CurrentUser, svc: DriveSvc
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.refresh_catalog(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.get(
    "/connectors/{connector_id}/folders",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def list_folders(
    connector_id: UUID, request: Request, user: CurrentUser, svc: DriveSvc
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.list_resources(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.put(
    "/connectors/{connector_id}/folders/selection",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def select_folders(
    connector_id: UUID,
    body: ResourceSelectionRequest,
    request: Request,
    user: CurrentUser,
    svc: DriveSvc,
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
    svc: DriveSvc,
) -> DataResponse[SyncJobOut]:
    job = svc.sync(
        connector_id=connector_id, user_id=user.id, resource_id=body.resource_id
    )
    job = svc.db.get(type(job), job.id) or job
    return DataResponse(
        data=SyncJobOut.model_validate(job),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )
