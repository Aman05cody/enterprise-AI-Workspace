"""Workspace, members, invites, departments routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Request

from eaw.api.deps import CurrentUser, OrgSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.orgs import (
    AcceptInviteRequest,
    AssignDepartmentsRequest,
    ChangeRoleRequest,
    CreateOrgRequest,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    InviteOut,
    InviteRequest,
    MemberOut,
    OrgOut,
    UpdateOrgRequest,
    UpdateSettingsRequest,
)

router = APIRouter(tags=["organizations"])


def _org_out(org, role: Optional[str] = None) -> OrgOut:
    return OrgOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        plan_tier=org.plan_tier,
        seat_limit=org.seat_limit,
        settings=org.settings or {},
        my_role=role,
    )


def _member_out(m) -> MemberOut:
    dept_ids = [d.department_id for d in (m.departments or [])]
    return MemberOut(
        user_id=m.user_id,
        email=m.user.email,
        full_name=m.user.full_name,
        role=m.role,
        status=m.status,
        department_ids=dept_ids,
    )


@router.post("/organizations", response_model=DataResponse[OrgOut], status_code=201)
def create_org(
    body: CreateOrgRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[OrgOut]:
    org = org_svc.create_organization(
        user_id=user.id, name=body.name, slug=body.slug
    )
    return DataResponse(
        data=_org_out(org, role="owner"),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/organizations", response_model=DataResponse[list[OrgOut]])
def list_orgs(
    request: Request, user: CurrentUser, org_svc: OrgSvc
) -> DataResponse[list[OrgOut]]:
    rows = org_svc.list_my_organizations(user.id)
    data = [_org_out(org, role=mem.role) for org, mem in rows]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(data),
        ),
    )


@router.get("/organizations/{org_id}", response_model=DataResponse[OrgOut])
def get_org(
    org_id: UUID, request: Request, user: CurrentUser, org_svc: OrgSvc
) -> DataResponse[OrgOut]:
    org, mem = org_svc.get_organization(org_id, user.id)
    return DataResponse(
        data=_org_out(org, role=mem.role),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch("/organizations/{org_id}", response_model=DataResponse[OrgOut])
def update_org(
    org_id: UUID,
    body: UpdateOrgRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[OrgOut]:
    org = org_svc.update_organization(
        org_id, user.id, name=body.name, logo_url=body.logo_url
    )
    _, mem = org_svc.get_organization(org_id, user.id)
    return DataResponse(
        data=_org_out(org, role=mem.role),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/organizations/{org_id}/settings", response_model=DataResponse[dict])
def get_settings(
    org_id: UUID, request: Request, user: CurrentUser, org_svc: OrgSvc
) -> DataResponse[dict]:
    settings = org_svc.get_settings(org_id, user.id)
    return DataResponse(
        data=settings,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch("/organizations/{org_id}/settings", response_model=DataResponse[dict])
def patch_settings(
    org_id: UUID,
    body: UpdateSettingsRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[dict]:
    settings = org_svc.update_settings(org_id, user.id, body.settings)
    return DataResponse(
        data=settings,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/organizations/{org_id}/members", response_model=DataResponse[list[MemberOut]]
)
def list_members(
    org_id: UUID, request: Request, user: CurrentUser, org_svc: OrgSvc
) -> DataResponse[list[MemberOut]]:
    members = org_svc.list_members(org_id, user.id)
    data = [_member_out(m) for m in members]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(data)
        ),
    )


@router.patch(
    "/organizations/{org_id}/members/{member_user_id}",
    response_model=DataResponse[MemberOut],
)
def change_role(
    org_id: UUID,
    member_user_id: UUID,
    body: ChangeRoleRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[MemberOut]:
    m = org_svc.change_role(org_id, user.id, member_user_id, body.role)
    # reload user relation
    members = {x.user_id: x for x in org_svc.list_members(org_id, user.id)}
    return DataResponse(
        data=_member_out(members[m.user_id]),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.delete(
    "/organizations/{org_id}/members/{member_user_id}",
    response_model=MessageResponse,
)
def remove_member(
    org_id: UUID,
    member_user_id: UUID,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> MessageResponse:
    org_svc.remove_member(org_id, user.id, member_user_id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.put(
    "/organizations/{org_id}/members/{member_user_id}/departments",
    response_model=DataResponse[MemberOut],
)
def assign_departments(
    org_id: UUID,
    member_user_id: UUID,
    body: AssignDepartmentsRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[MemberOut]:
    org_svc.assign_departments(
        org_id, user.id, member_user_id, body.department_ids
    )
    members = {x.user_id: x for x in org_svc.list_members(org_id, user.id)}
    return DataResponse(
        data=_member_out(members[member_user_id]),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/organizations/{org_id}/invites",
    response_model=DataResponse[InviteOut],
    status_code=201,
)
def create_invite(
    org_id: UUID,
    body: InviteRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[InviteOut]:
    invite, raw = org_svc.create_invite(
        org_id,
        user.id,
        email=body.email,
        role=body.role,
        department_id=body.department_id,
    )
    return DataResponse(
        data=InviteOut(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            department_id=invite.department_id,
            expires_at=invite.expires_at.isoformat(),
            token=raw,
        ),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/organizations/{org_id}/invites", response_model=DataResponse[list[InviteOut]]
)
def list_invites(
    org_id: UUID, request: Request, user: CurrentUser, org_svc: OrgSvc
) -> DataResponse[list[InviteOut]]:
    invites = org_svc.list_invites(org_id, user.id)
    data = [
        InviteOut(
            id=i.id,
            email=i.email,
            role=i.role,
            status=i.status,
            department_id=i.department_id,
            expires_at=i.expires_at.isoformat(),
        )
        for i in invites
    ]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(data)
        ),
    )


@router.post("/invites/accept", response_model=DataResponse[MemberOut])
def accept_invite(
    body: AcceptInviteRequest,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[MemberOut]:
    membership = org_svc.accept_invite(token=body.token, user_id=user.id)
    members = {
        x.user_id: x
        for x in org_svc.list_members(membership.organization_id, user.id)
    }
    return DataResponse(
        data=_member_out(members[user.id]),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/organizations/{org_id}/departments",
    response_model=DataResponse[list[DepartmentOut]],
)
def list_departments(
    org_id: UUID, request: Request, user: CurrentUser, org_svc: OrgSvc
) -> DataResponse[list[DepartmentOut]]:
    depts = org_svc.list_departments(org_id, user.id)
    data = [DepartmentOut.model_validate(d) for d in depts]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None), total=len(data)
        ),
    )


@router.post(
    "/organizations/{org_id}/departments",
    response_model=DataResponse[DepartmentOut],
    status_code=201,
)
def create_department(
    org_id: UUID,
    body: DepartmentCreate,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[DepartmentOut]:
    dept = org_svc.create_department(
        org_id, user.id, name=body.name, description=body.description
    )
    return DataResponse(
        data=DepartmentOut.model_validate(dept),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch("/departments/{dept_id}", response_model=DataResponse[DepartmentOut])
def update_department(
    dept_id: UUID,
    body: DepartmentUpdate,
    request: Request,
    user: CurrentUser,
    org_svc: OrgSvc,
) -> DataResponse[DepartmentOut]:
    dept = org_svc.update_department(
        dept_id, user.id, name=body.name, description=body.description
    )
    return DataResponse(
        data=DepartmentOut.model_validate(dept),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.delete("/departments/{dept_id}", response_model=MessageResponse)
def delete_department(
    dept_id: UUID, request: Request, user: CurrentUser, org_svc: OrgSvc
) -> MessageResponse:
    org_svc.delete_department(dept_id, user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )
