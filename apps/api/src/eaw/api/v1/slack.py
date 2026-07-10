"""Slack connector routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from eaw.api.deps import CurrentUser, SlackSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.connectors import (
    ConnectorOut,
    ConnectorResourceOut,
    ResourceSelectionRequest,
    SlackChannelSummaryRequest,
    SlackConnectRequest,
    SlackMeetingRecapRequest,
    SlackSearchRequest,
    SyncJobOut,
    SyncRequest,
)

router = APIRouter(prefix="/slack", tags=["slack"])


def _connector_out(c) -> ConnectorOut:
    return ConnectorOut(
        id=c.id,
        organization_id=c.organization_id,
        type=c.type,
        status=c.status,
        display_name=c.display_name,
        config=dict(c.config or {}),
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
    body: SlackConnectRequest, request: Request, user: CurrentUser, svc: SlackSvc
) -> DataResponse[ConnectorOut]:
    c = svc.connect(
        organization_id=body.organization_id,
        user_id=user.id,
        bot_token=body.bot_token,
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
    svc: SlackSvc,
    organization_id: UUID = Query(...),
) -> DataResponse[list[ConnectorOut]]:
    rows = svc.list_connectors(organization_id=organization_id, user_id=user.id)
    return DataResponse(
        data=[_connector_out(c) for c in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.delete("/connectors/{connector_id}", response_model=MessageResponse)
def disconnect(
    connector_id: UUID, request: Request, user: CurrentUser, svc: SlackSvc
) -> MessageResponse:
    svc.disconnect(connector_id=connector_id, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/connectors/{connector_id}/refresh-channels",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def refresh_channels(
    connector_id: UUID, request: Request, user: CurrentUser, svc: SlackSvc
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.refresh_catalog(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.get(
    "/connectors/{connector_id}/channels",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def list_channels(
    connector_id: UUID, request: Request, user: CurrentUser, svc: SlackSvc
) -> DataResponse[list[ConnectorResourceOut]]:
    rows = svc.list_resources(connector_id=connector_id, user_id=user.id)
    return DataResponse(
        data=[_resource_out(r) for r in rows],
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(rows)),
    )


@router.put(
    "/connectors/{connector_id}/channels/selection",
    response_model=DataResponse[list[ConnectorResourceOut]],
)
def select_channels(
    connector_id: UUID,
    body: ResourceSelectionRequest,
    request: Request,
    user: CurrentUser,
    svc: SlackSvc,
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
    svc: SlackSvc,
) -> DataResponse[SyncJobOut]:
    job = svc.sync(
        connector_id=connector_id, user_id=user.id, resource_id=body.resource_id
    )
    job = svc.db.get(type(job), job.id) or job
    return DataResponse(
        data=SyncJobOut.model_validate(job),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/connectors/{connector_id}/channel-summary",
    response_model=DataResponse[dict[str, Any]],
)
def channel_summary(
    connector_id: UUID,
    body: SlackChannelSummaryRequest,
    request: Request,
    user: CurrentUser,
    svc: SlackSvc,
) -> DataResponse[dict[str, Any]]:
    data = svc.channel_summary(
        connector_id=connector_id,
        user_id=user.id,
        resource_id=body.resource_id,
        limit=body.limit,
    )
    return DataResponse(
        data=data, meta=Meta(request_id=getattr(request.state, "request_id", None))
    )


@router.post(
    "/connectors/{connector_id}/meeting-recap",
    response_model=DataResponse[dict[str, Any]],
)
def meeting_recap(
    connector_id: UUID,
    body: SlackMeetingRecapRequest,
    request: Request,
    user: CurrentUser,
    svc: SlackSvc,
) -> DataResponse[dict[str, Any]]:
    data = svc.meeting_recap(
        connector_id=connector_id,
        user_id=user.id,
        resource_id=body.resource_id,
        thread_ts=body.thread_ts,
        limit=body.limit,
    )
    return DataResponse(
        data=data, meta=Meta(request_id=getattr(request.state, "request_id", None))
    )


@router.post(
    "/connectors/{connector_id}/search",
    response_model=DataResponse[dict[str, Any]],
)
def search(
    connector_id: UUID,
    body: SlackSearchRequest,
    request: Request,
    user: CurrentUser,
    svc: SlackSvc,
) -> DataResponse[dict[str, Any]]:
    data = svc.ai_search(
        connector_id=connector_id, user_id=user.id, query=body.query
    )
    return DataResponse(
        data=data, meta=Meta(request_id=getattr(request.state, "request_id", None))
    )
