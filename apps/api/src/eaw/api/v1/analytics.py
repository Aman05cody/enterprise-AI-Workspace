"""Admin analytics and audit routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Request

from eaw.api.deps import AnalyticsSvc, CurrentUser
from eaw.api.schemas.analytics import AuditLogOut, OverviewOut
from eaw.api.schemas.common import DataResponse, Meta

router = APIRouter(tags=["analytics"])


@router.get(
    "/organizations/{org_id}/analytics/overview",
    response_model=DataResponse[OverviewOut],
)
def overview(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    days: int = Query(30, ge=1, le=365),
) -> DataResponse[OverviewOut]:
    data = svc.overview(organization_id=org_id, user_id=user.id, days=days)
    return DataResponse(
        data=OverviewOut(**data),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/organizations/{org_id}/analytics/usage",
    response_model=DataResponse[list[dict[str, Any]]],
)
def usage(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    days: int = Query(14, ge=1, le=90),
) -> DataResponse[list[dict[str, Any]]]:
    data = svc.usage_timeseries(organization_id=org_id, user_id=user.id, days=days)
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(data)),
    )


@router.get(
    "/organizations/{org_id}/analytics/popular-documents",
    response_model=DataResponse[list[dict[str, Any]]],
)
def popular_documents(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    limit: int = Query(10, ge=1, le=50),
) -> DataResponse[list[dict[str, Any]]]:
    data = svc.popular_documents(
        organization_id=org_id, user_id=user.id, limit=limit
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(data)),
    )


@router.get(
    "/organizations/{org_id}/analytics/departments",
    response_model=DataResponse[list[dict[str, Any]]],
)
def departments(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    days: int = Query(30, ge=1, le=365),
) -> DataResponse[list[dict[str, Any]]]:
    data = svc.department_activity(
        organization_id=org_id, user_id=user.id, days=days
    )
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(data)),
    )


@router.get(
    "/organizations/{org_id}/analytics/storage",
    response_model=DataResponse[dict[str, Any]],
)
def storage(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
) -> DataResponse[dict[str, Any]]:
    data = svc.storage_breakdown(organization_id=org_id, user_id=user.id)
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/organizations/{org_id}/analytics/search-trends",
    response_model=DataResponse[list[dict[str, Any]]],
)
def search_trends(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    days: int = Query(30, ge=1, le=365),
) -> DataResponse[list[dict[str, Any]]]:
    data = svc.search_trends(organization_id=org_id, user_id=user.id, days=days)
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(data)),
    )


@router.get(
    "/organizations/{org_id}/analytics/top-users",
    response_model=DataResponse[list[dict[str, Any]]],
)
def top_users(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    days: int = Query(30, ge=1, le=365),
) -> DataResponse[list[dict[str, Any]]]:
    data = svc.top_users(organization_id=org_id, user_id=user.id, days=days)
    return DataResponse(
        data=data,
        meta=Meta(request_id=getattr(request.state, "request_id", None), total=len(data)),
    )


@router.get(
    "/organizations/{org_id}/audit-logs",
    response_model=DataResponse[list[AuditLogOut]],
)
def audit_logs(
    org_id: UUID,
    request: Request,
    user: CurrentUser,
    svc: AnalyticsSvc,
    action: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> DataResponse[list[AuditLogOut]]:
    rows, total = svc.list_audit_logs(
        organization_id=org_id,
        user_id=user.id,
        action=action,
        limit=limit,
        offset=offset,
    )
    data = [
        AuditLogOut(
            id=r.id,
            organization_id=r.organization_id,
            actor_user_id=r.actor_user_id,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            metadata=r.metadata_ or {},
            created_at=r.created_at,
        )
        for r in rows
    ]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            page=offset // limit + 1 if limit else 1,
            page_size=limit,
            total=total,
        ),
    )
