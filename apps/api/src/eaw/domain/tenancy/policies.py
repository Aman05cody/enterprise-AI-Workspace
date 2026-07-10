"""RBAC policies for workspace actions."""

from eaw.domain.common.enums import MembershipRole, role_at_least
from eaw.domain.common.errors import ForbiddenError


def require_role(
    current: MembershipRole | str,
    minimum: MembershipRole,
    *,
    action: str = "perform this action",
) -> None:
    if not role_at_least(current, minimum):
        raise ForbiddenError(
            f"Insufficient permissions to {action}",
            details={"required_role": minimum.value, "current_role": str(current)},
        )


def can_manage_members(role: MembershipRole | str) -> bool:
    return role_at_least(role, MembershipRole.ADMIN)


def can_manage_workspace(role: MembershipRole | str) -> bool:
    return role_at_least(role, MembershipRole.ADMIN)


def can_manage_departments(role: MembershipRole | str) -> bool:
    return role_at_least(role, MembershipRole.ADMIN)


def can_assign_owner(actor: MembershipRole | str) -> bool:
    return MembershipRole(actor) == MembershipRole.OWNER


def can_manage_knowledge_bases(role: MembershipRole | str) -> bool:
    """Create/update knowledge bases — managers and above."""
    return role_at_least(role, MembershipRole.MANAGER)


def can_delete_knowledge_bases(role: MembershipRole | str) -> bool:
    return role_at_least(role, MembershipRole.ADMIN)


def can_upload_documents(role: MembershipRole | str) -> bool:
    return role_at_least(role, MembershipRole.EMPLOYEE)


def can_delete_any_document(role: MembershipRole | str) -> bool:
    return role_at_least(role, MembershipRole.MANAGER)


def can_read_knowledge(role: MembershipRole | str) -> bool:
    """Guests and above may read/search documents they can access."""
    return role_at_least(role, MembershipRole.GUEST)
