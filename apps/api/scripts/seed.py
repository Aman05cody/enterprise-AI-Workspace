"""Seed demo owner + workspace for local development."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python -m scripts.seed` from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select

from eaw.application.services.audit_service import AuditService
from eaw.application.services.auth_service import AuthService
from eaw.application.services.org_service import OrgService
from eaw.core.config import get_settings
from eaw.domain.common.enums import MembershipRole
from eaw.infrastructure.db.models.identity import User
from eaw.infrastructure.db.session import SessionLocal
from eaw.infrastructure.email.console_email import ConsoleEmailAdapter


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    email = ConsoleEmailAdapter()
    audit = AuditService(db)
    auth = AuthService(db, settings, email, audit)
    org = OrgService(db, settings, email, audit)

    existing = db.scalar(select(User).where(User.email == "owner@example.com"))
    if existing:
        print("Seed already applied (owner@example.com exists).")
        db.close()
        return

    user, access, refresh = auth.register(
        email="owner@example.com",
        password="Owner123!",
        full_name="Demo Owner",
    )
    workspace = org.create_organization(
        user_id=user.id, name="Acme Corp", slug="acme"
    )
    org.create_department(
        workspace.id, user.id, name="Engineering", description="Product engineering"
    )
    org.create_department(workspace.id, user.id, name="People", description="HR")

    print("Seed complete")
    print(f"  email:    owner@example.com")
    print(f"  password: Owner123!")
    print(f"  org:      {workspace.name} ({workspace.slug}) id={workspace.id}")
    print(f"  access:   {access[:24]}...")
    print(f"  refresh:  {refresh[:24]}...")
    db.close()


if __name__ == "__main__":
    main()
