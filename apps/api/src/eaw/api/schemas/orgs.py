"""Organization / RBAC schemas."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from eaw.domain.common.enums import MembershipRole


class CreateOrgRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=100)


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    logo_url: Optional[str] = None


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    plan_tier: str
    seat_limit: Optional[int] = None
    settings: dict[str, Any] = Field(default_factory=dict)
    my_role: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, Any]


class MemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: str
    status: str
    department_ids: list[UUID] = Field(default_factory=list)


class ChangeRoleRequest(BaseModel):
    role: MembershipRole


class InviteRequest(BaseModel):
    email: EmailStr
    role: MembershipRole = MembershipRole.EMPLOYEE
    department_id: Optional[UUID] = None


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    status: str
    department_id: Optional[UUID] = None
    expires_at: str
    # raw token only returned once on create for dev convenience
    token: Optional[str] = None


class AcceptInviteRequest(BaseModel):
    token: str


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None


class AssignDepartmentsRequest(BaseModel):
    department_ids: list[UUID]
