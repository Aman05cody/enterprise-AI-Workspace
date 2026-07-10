"""RBAC policy unit tests."""

import pytest

from eaw.domain.common.enums import MembershipRole, role_at_least
from eaw.domain.common.errors import ForbiddenError
from eaw.domain.tenancy.policies import require_role


def test_role_hierarchy() -> None:
    assert role_at_least(MembershipRole.ADMIN, MembershipRole.MANAGER)
    assert role_at_least(MembershipRole.OWNER, MembershipRole.ADMIN)
    assert not role_at_least(MembershipRole.EMPLOYEE, MembershipRole.ADMIN)
    assert role_at_least(MembershipRole.GUEST, MembershipRole.GUEST)


def test_require_role_raises() -> None:
    with pytest.raises(ForbiddenError):
        require_role(MembershipRole.EMPLOYEE, MembershipRole.ADMIN, action="manage")


def test_require_role_ok() -> None:
    require_role(MembershipRole.ADMIN, MembershipRole.ADMIN, action="manage")
