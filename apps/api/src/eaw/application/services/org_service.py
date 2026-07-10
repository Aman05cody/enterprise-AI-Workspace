"""Organization, membership, department, and invite use cases."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from eaw.application.ports.email import EmailPort
from eaw.application.services.audit_service import AuditService
from eaw.core.config import Settings
from eaw.core.security import generate_opaque_token, hash_token
from eaw.domain.common.enums import (
    InviteStatus,
    MembershipRole,
    MembershipStatus,
    role_at_least,
)
from eaw.domain.common.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)
from eaw.domain.tenancy.policies import (
    can_assign_owner,
    can_manage_departments,
    can_manage_members,
    can_manage_workspace,
    require_role,
)
from eaw.infrastructure.db.models.identity import User
from eaw.infrastructure.db.models.tenancy import (
    Department,
    Invite,
    Membership,
    MembershipDepartment,
    Organization,
)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class OrgService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        email: EmailPort,
        audit: AuditService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.email = email
        self.audit = audit

    # ── helpers ──────────────────────────────────────────────

    def get_membership(self, org_id: UUID, user_id: UUID) -> Membership:
        m = self.db.scalar(
            select(Membership)
            .options(selectinload(Membership.departments))
            .where(
                Membership.organization_id == org_id,
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE.value,
            )
        )
        if m is None:
            raise ForbiddenError("You are not a member of this workspace")
        return m

    def require_org(self, org_id: UUID) -> Organization:
        org = self.db.get(Organization, org_id)
        if org is None or org.deleted_at is not None:
            raise NotFoundError("Workspace not found")
        return org

    def _slugify(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
        slug = base[:80]
        candidate = slug
        i = 1
        while self.db.scalar(select(Organization.id).where(Organization.slug == candidate)):
            i += 1
            candidate = f"{slug}-{i}"
        return candidate

    def _count_owners(self, org_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Membership)
                .where(
                    Membership.organization_id == org_id,
                    Membership.role == MembershipRole.OWNER.value,
                    Membership.status == MembershipStatus.ACTIVE.value,
                )
            )
            or 0
        )

    # ── organizations ────────────────────────────────────────

    def create_organization(
        self, *, user_id: UUID, name: str, slug: Optional[str] = None
    ) -> Organization:
        name = name.strip()
        if not name:
            raise ValidationAppError("Workspace name is required")
        if slug:
            slug = slug.strip().lower()
            if not _SLUG_RE.match(slug):
                raise ValidationAppError(
                    "Slug must be lowercase alphanumeric with hyphens"
                )
            if self.db.scalar(select(Organization.id).where(Organization.slug == slug)):
                raise ConflictError("Workspace slug already exists")
        else:
            slug = self._slugify(name)

        org = Organization(
            name=name,
            slug=slug,
            settings={
                "ai": {"default_model": None, "temperature": 0.2},
                "limits": {"max_upload_mb": 50},
            },
            plan_tier="free",
            seat_limit=10,
            created_by=user_id,
        )
        self.db.add(org)
        self.db.flush()
        self.db.add(
            Membership(
                organization_id=org.id,
                user_id=user_id,
                role=MembershipRole.OWNER.value,
                status=MembershipStatus.ACTIVE.value,
            )
        )
        self.audit.log(
            action="org.created",
            actor_user_id=user_id,
            organization_id=org.id,
            resource_type="organization",
            resource_id=org.id,
            metadata={"name": name, "slug": slug},
        )
        self.db.commit()
        self.db.refresh(org)
        return org

    def list_my_organizations(self, user_id: UUID) -> list[tuple[Organization, Membership]]:
        rows = self.db.execute(
            select(Organization, Membership)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE.value,
                Organization.deleted_at.is_(None),
            )
            .order_by(Organization.name)
        ).all()
        return [(org, mem) for org, mem in rows]

    def get_organization(self, org_id: UUID, user_id: UUID) -> tuple[Organization, Membership]:
        org = self.require_org(org_id)
        mem = self.get_membership(org_id, user_id)
        return org, mem

    def update_organization(
        self,
        org_id: UUID,
        user_id: UUID,
        *,
        name: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> Organization:
        org, mem = self.get_organization(org_id, user_id)
        require_role(mem.role, MembershipRole.ADMIN, action="update workspace")
        if name is not None:
            org.name = name.strip()
        if logo_url is not None:
            org.logo_url = logo_url
        self.audit.log(
            action="org.updated",
            actor_user_id=user_id,
            organization_id=org_id,
            resource_type="organization",
            resource_id=org_id,
        )
        self.db.commit()
        self.db.refresh(org)
        return org

    def get_settings(self, org_id: UUID, user_id: UUID) -> dict:
        org, mem = self.get_organization(org_id, user_id)
        require_role(mem.role, MembershipRole.ADMIN, action="view settings")
        return org.settings or {}

    def update_settings(self, org_id: UUID, user_id: UUID, settings: dict) -> dict:
        org, mem = self.get_organization(org_id, user_id)
        require_role(mem.role, MembershipRole.ADMIN, action="update settings")
        merged = {**(org.settings or {}), **settings}
        org.settings = merged
        self.audit.log(
            action="org.settings_updated",
            actor_user_id=user_id,
            organization_id=org_id,
            resource_type="organization",
            resource_id=org_id,
        )
        self.db.commit()
        return merged

    # ── members ──────────────────────────────────────────────

    def list_members(self, org_id: UUID, user_id: UUID) -> list[Membership]:
        self.get_membership(org_id, user_id)
        return list(
            self.db.scalars(
                select(Membership)
                .options(
                    selectinload(Membership.user),
                    selectinload(Membership.departments),
                )
                .where(
                    Membership.organization_id == org_id,
                    Membership.status == MembershipStatus.ACTIVE.value,
                )
                .order_by(Membership.created_at)
            ).all()
        )

    def change_role(
        self,
        org_id: UUID,
        actor_id: UUID,
        target_user_id: UUID,
        new_role: MembershipRole,
    ) -> Membership:
        actor = self.get_membership(org_id, actor_id)
        if not can_manage_members(actor.role):
            raise ForbiddenError("Insufficient permissions to change roles")
        if new_role == MembershipRole.OWNER and not can_assign_owner(actor.role):
            raise ForbiddenError("Only an owner can assign the owner role")

        target = self.db.scalar(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(
                Membership.organization_id == org_id,
                Membership.user_id == target_user_id,
                Membership.status == MembershipStatus.ACTIVE.value,
            )
        )
        if target is None:
            raise NotFoundError("Member not found")

        if (
            target.role == MembershipRole.OWNER.value
            and new_role != MembershipRole.OWNER
            and self._count_owners(org_id) <= 1
        ):
            raise ValidationAppError("Cannot demote the last owner")

        old = target.role
        target.role = new_role.value
        self.audit.log(
            action="member.role_changed",
            actor_user_id=actor_id,
            organization_id=org_id,
            resource_type="user",
            resource_id=target_user_id,
            metadata={"from": old, "to": new_role.value},
        )
        self.db.commit()
        self.db.refresh(target)
        return target

    def remove_member(self, org_id: UUID, actor_id: UUID, target_user_id: UUID) -> None:
        actor = self.get_membership(org_id, actor_id)
        if not can_manage_members(actor.role):
            raise ForbiddenError("Insufficient permissions to remove members")

        target = self.db.scalar(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.user_id == target_user_id,
                Membership.status == MembershipStatus.ACTIVE.value,
            )
        )
        if target is None:
            raise NotFoundError("Member not found")
        if target.role == MembershipRole.OWNER.value and self._count_owners(org_id) <= 1:
            raise ValidationAppError("Cannot remove the last owner")
        if target_user_id == actor_id and target.role == MembershipRole.OWNER.value:
            if self._count_owners(org_id) <= 1:
                raise ValidationAppError("Cannot remove the last owner")

        target.status = MembershipStatus.DISABLED.value
        self.audit.log(
            action="member.removed",
            actor_user_id=actor_id,
            organization_id=org_id,
            resource_type="user",
            resource_id=target_user_id,
        )
        self.db.commit()

    def assign_departments(
        self,
        org_id: UUID,
        actor_id: UUID,
        target_user_id: UUID,
        department_ids: list[UUID],
    ) -> Membership:
        actor = self.get_membership(org_id, actor_id)
        if not can_manage_members(actor.role):
            raise ForbiddenError("Insufficient permissions")
        target = self.db.scalar(
            select(Membership)
            .options(selectinload(Membership.departments))
            .where(
                Membership.organization_id == org_id,
                Membership.user_id == target_user_id,
                Membership.status == MembershipStatus.ACTIVE.value,
            )
        )
        if target is None:
            raise NotFoundError("Member not found")

        for dept_id in department_ids:
            dept = self.db.get(Department, dept_id)
            if (
                dept is None
                or dept.organization_id != org_id
                or dept.deleted_at is not None
            ):
                raise NotFoundError(f"Department {dept_id} not found in workspace")

        target.departments.clear()
        self.db.flush()
        for dept_id in department_ids:
            target.departments.append(
                MembershipDepartment(membership_id=target.id, department_id=dept_id)
            )
        self.audit.log(
            action="member.departments_assigned",
            actor_user_id=actor_id,
            organization_id=org_id,
            resource_type="user",
            resource_id=target_user_id,
            metadata={"department_ids": [str(d) for d in department_ids]},
        )
        self.db.commit()
        self.db.refresh(target)
        return target

    # ── invites ──────────────────────────────────────────────

    def create_invite(
        self,
        org_id: UUID,
        actor_id: UUID,
        *,
        email: str,
        role: MembershipRole,
        department_id: Optional[UUID] = None,
    ) -> tuple[Invite, str]:
        actor = self.get_membership(org_id, actor_id)
        if not can_manage_members(actor.role):
            raise ForbiddenError("Insufficient permissions to invite")
        if role == MembershipRole.OWNER and not can_assign_owner(actor.role):
            raise ForbiddenError("Only an owner can invite another owner")

        email_n = email.strip().lower()
        existing_user = self.db.scalar(select(User).where(User.email == email_n))
        if existing_user:
            existing_mem = self.db.scalar(
                select(Membership).where(
                    Membership.organization_id == org_id,
                    Membership.user_id == existing_user.id,
                    Membership.status == MembershipStatus.ACTIVE.value,
                )
            )
            if existing_mem:
                raise ConflictError("User is already a member")

        if department_id:
            dept = self.db.get(Department, department_id)
            if not dept or dept.organization_id != org_id or dept.deleted_at:
                raise NotFoundError("Department not found")

        raw = generate_opaque_token()
        invite = Invite(
            organization_id=org_id,
            email=email_n,
            role=role.value,
            department_id=department_id,
            token_hash=hash_token(raw),
            status=InviteStatus.PENDING.value,
            invited_by=actor_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(invite)
        org = self.require_org(org_id)
        url = f"{self.settings.web_url}/invites/accept?token={raw}"
        self.email.send(
            to=email_n,
            subject=f"You're invited to {org.name}",
            body=(
                f"You have been invited to join {org.name} as {role.value}.\n\n"
                f"Accept invite:\n{url}\n"
            ),
        )
        self.audit.log(
            action="member.invited",
            actor_user_id=actor_id,
            organization_id=org_id,
            resource_type="invite",
            metadata={"email": email_n, "role": role.value},
        )
        self.db.commit()
        self.db.refresh(invite)
        return invite, raw

    def list_invites(self, org_id: UUID, actor_id: UUID) -> list[Invite]:
        actor = self.get_membership(org_id, actor_id)
        if not can_manage_members(actor.role):
            raise ForbiddenError("Insufficient permissions")
        return list(
            self.db.scalars(
                select(Invite)
                .where(
                    Invite.organization_id == org_id,
                    Invite.status == InviteStatus.PENDING.value,
                )
                .order_by(Invite.created_at.desc())
            ).all()
        )

    def accept_invite(self, *, token: str, user_id: UUID) -> Membership:
        token_hash = hash_token(token)
        now = datetime.now(timezone.utc)
        invite = self.db.scalar(
            select(Invite).where(Invite.token_hash == token_hash)
        )
        if (
            invite is None
            or invite.status != InviteStatus.PENDING.value
            or invite.expires_at < now
        ):
            raise ValidationAppError("Invalid or expired invite")

        user = self.db.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.email.lower() != invite.email.lower():
            raise ForbiddenError("Invite email does not match your account")

        existing = self.db.scalar(
            select(Membership).where(
                Membership.organization_id == invite.organization_id,
                Membership.user_id == user_id,
            )
        )
        if existing:
            existing.status = MembershipStatus.ACTIVE.value
            existing.role = invite.role
            membership = existing
        else:
            membership = Membership(
                organization_id=invite.organization_id,
                user_id=user_id,
                role=invite.role,
                status=MembershipStatus.ACTIVE.value,
            )
            self.db.add(membership)
            self.db.flush()

        if invite.department_id:
            self.db.add(
                MembershipDepartment(
                    membership_id=membership.id,
                    department_id=invite.department_id,
                )
            )

        invite.status = InviteStatus.ACCEPTED.value
        invite.accepted_at = now
        self.audit.log(
            action="member.invite_accepted",
            actor_user_id=user_id,
            organization_id=invite.organization_id,
            resource_type="membership",
            resource_id=membership.id,
        )
        self.db.commit()
        self.db.refresh(membership)
        return membership

    # ── departments ──────────────────────────────────────────

    def list_departments(self, org_id: UUID, user_id: UUID) -> list[Department]:
        self.get_membership(org_id, user_id)
        return list(
            self.db.scalars(
                select(Department)
                .where(
                    Department.organization_id == org_id,
                    Department.deleted_at.is_(None),
                )
                .order_by(Department.name)
            ).all()
        )

    def create_department(
        self,
        org_id: UUID,
        user_id: UUID,
        *,
        name: str,
        description: Optional[str] = None,
    ) -> Department:
        mem = self.get_membership(org_id, user_id)
        if not can_manage_departments(mem.role):
            raise ForbiddenError("Insufficient permissions to manage departments")
        name = name.strip()
        if not name:
            raise ValidationAppError("Department name is required")
        exists = self.db.scalar(
            select(Department).where(
                Department.organization_id == org_id,
                Department.name == name,
                Department.deleted_at.is_(None),
            )
        )
        if exists:
            raise ConflictError("Department already exists")
        dept = Department(
            organization_id=org_id, name=name, description=description
        )
        self.db.add(dept)
        self.audit.log(
            action="department.created",
            actor_user_id=user_id,
            organization_id=org_id,
            resource_type="department",
            metadata={"name": name},
        )
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def update_department(
        self,
        dept_id: UUID,
        user_id: UUID,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Department:
        dept = self.db.get(Department, dept_id)
        if dept is None or dept.deleted_at is not None:
            raise NotFoundError("Department not found")
        mem = self.get_membership(dept.organization_id, user_id)
        if not can_manage_departments(mem.role):
            raise ForbiddenError("Insufficient permissions")
        if name is not None:
            dept.name = name.strip()
        if description is not None:
            dept.description = description
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def delete_department(self, dept_id: UUID, user_id: UUID) -> None:
        dept = self.db.get(Department, dept_id)
        if dept is None or dept.deleted_at is not None:
            raise NotFoundError("Department not found")
        mem = self.get_membership(dept.organization_id, user_id)
        if not can_manage_departments(mem.role):
            raise ForbiddenError("Insufficient permissions")
        dept.deleted_at = datetime.now(timezone.utc)
        self.audit.log(
            action="department.deleted",
            actor_user_id=user_id,
            organization_id=dept.organization_id,
            resource_type="department",
            resource_id=dept.id,
        )
        self.db.commit()
