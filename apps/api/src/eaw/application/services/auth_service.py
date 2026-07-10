"""Authentication use cases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eaw.application.ports.email import EmailPort
from eaw.application.services.audit_service import AuditService
from eaw.core.config import Settings
from eaw.core.security import (
    create_access_token,
    generate_opaque_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from eaw.domain.common.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)
from eaw.infrastructure.db.models.identity import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)


class AuthService:
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

    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, str, str]:
        email_n = email.strip().lower()
        self._validate_password(password)
        existing = self.db.scalar(select(User).where(User.email == email_n))
        if existing and existing.deleted_at is None:
            raise ConflictError("An account with this email already exists")

        user = User(
            email=email_n,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()

        raw_verify = generate_opaque_token()
        self.db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(raw_verify),
                expires_at=datetime.now(timezone.utc) + timedelta(days=2),
                created_at=datetime.now(timezone.utc),
            )
        )
        verify_url = f"{self.settings.web_url}/verify-email?token={raw_verify}"
        self.email.send(
            to=user.email,
            subject="Verify your email — Enterprise AI Workspace",
            body=f"Welcome {user.full_name}!\n\nVerify your email:\n{verify_url}\n",
        )

        access, refresh = self._issue_tokens(user, ip=ip, user_agent=user_agent)
        self.audit.log(
            action="auth.register",
            actor_user_id=user.id,
            ip_address=ip,
            user_agent=user_agent,
            resource_type="user",
            resource_id=user.id,
        )
        self.db.commit()
        self.db.refresh(user)
        return user, access, refresh

    def login(
        self,
        *,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, str, str]:
        email_n = email.strip().lower()
        user = self.db.scalar(select(User).where(User.email == email_n))
        if (
            user is None
            or user.deleted_at is not None
            or not user.is_active
            or not user.password_hash
            or not verify_password(password, user.password_hash)
        ):
            raise UnauthorizedError("Invalid email or password")

        user.last_login_at = datetime.now(timezone.utc)
        access, refresh = self._issue_tokens(user, ip=ip, user_agent=user_agent)
        self.audit.log(
            action="auth.login",
            actor_user_id=user.id,
            ip_address=ip,
            user_agent=user_agent,
        )
        self.db.commit()
        self.db.refresh(user)
        return user, access, refresh

    def refresh(
        self,
        *,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, str, str]:
        token_hash = hash_token(refresh_token)
        now = datetime.now(timezone.utc)
        row = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if (
            row is None
            or row.revoked_at is not None
            or row.expires_at < now
        ):
            raise UnauthorizedError("Invalid or expired refresh token")

        user = self.db.get(User, row.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise UnauthorizedError("User is not active")

        row.revoked_at = now
        access, new_refresh = self._issue_tokens(user, ip=ip, user_agent=user_agent)
        self.db.commit()
        self.db.refresh(user)
        return user, access, new_refresh

    def logout(self, *, refresh_token: str, user_id: UUID) -> None:
        token_hash = hash_token(refresh_token)
        row = self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
            )
        )
        if row and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            self.audit.log(action="auth.logout", actor_user_id=user_id)
            self.db.commit()

    def get_user(self, user_id: UUID) -> User:
        user = self.db.get(User, user_id)
        if user is None or user.deleted_at is not None:
            raise NotFoundError("User not found")
        return user

    def update_profile(
        self, user_id: UUID, *, full_name: Optional[str] = None, avatar_url: Optional[str] = None
    ) -> User:
        user = self.get_user(user_id)
        if full_name is not None:
            user.full_name = full_name.strip()
        if avatar_url is not None:
            user.avatar_url = avatar_url
        self.db.commit()
        self.db.refresh(user)
        return user

    def verify_email(self, token: str) -> User:
        token_hash = hash_token(token)
        now = datetime.now(timezone.utc)
        row = self.db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        if row is None or row.used_at is not None or row.expires_at < now:
            raise ValidationAppError("Invalid or expired verification token")
        user = self.get_user(row.user_id)
        user.email_verified_at = now
        row.used_at = now
        self.audit.log(
            action="auth.email_verified",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def resend_verification(self, user_id: UUID) -> None:
        user = self.get_user(user_id)
        if user.email_verified_at is not None:
            return
        raw = generate_opaque_token()
        self.db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(timezone.utc) + timedelta(days=2),
                created_at=datetime.now(timezone.utc),
            )
        )
        url = f"{self.settings.web_url}/verify-email?token={raw}"
        self.email.send(
            to=user.email,
            subject="Verify your email — Enterprise AI Workspace",
            body=f"Verify your email:\n{url}\n",
        )
        self.db.commit()

    def forgot_password(self, email: str) -> None:
        """Always succeeds to avoid email enumeration."""
        email_n = email.strip().lower()
        user = self.db.scalar(select(User).where(User.email == email_n))
        if user and user.deleted_at is None and user.password_hash:
            raw = generate_opaque_token()
            self.db.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=hash_token(raw),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    created_at=datetime.now(timezone.utc),
                )
            )
            url = f"{self.settings.web_url}/reset-password?token={raw}"
            self.email.send(
                to=user.email,
                subject="Reset your password — Enterprise AI Workspace",
                body=f"Reset your password (valid 1 hour):\n{url}\n",
            )
            self.db.commit()

    def reset_password(self, *, token: str, new_password: str) -> None:
        self._validate_password(new_password)
        token_hash = hash_token(token)
        now = datetime.now(timezone.utc)
        row = self.db.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        if row is None or row.used_at is not None or row.expires_at < now:
            raise ValidationAppError("Invalid or expired reset token")
        user = self.get_user(row.user_id)
        user.password_hash = hash_password(new_password)
        row.used_at = now
        # revoke all refresh tokens
        tokens = self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        ).all()
        for t in tokens:
            t.revoked_at = now
        self.audit.log(
            action="auth.password_reset",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )
        self.db.commit()

    def _issue_tokens(
        self,
        user: User,
        *,
        ip: Optional[str],
        user_agent: Optional[str],
    ) -> tuple[str, str]:
        access = create_access_token(subject=user.id, extra={"email": user.email})
        raw_refresh = generate_refresh_token()
        expires = datetime.now(timezone.utc) + timedelta(
            days=self.settings.refresh_token_ttl_days
        )
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                expires_at=expires,
                user_agent=user_agent,
                ip_address=ip,
                created_at=datetime.now(timezone.utc),
            )
        )
        return access, raw_refresh

    def _validate_password(self, password: str) -> None:
        if len(password) < self.settings.password_min_length:
            raise ValidationAppError(
                f"Password must be at least {self.settings.password_min_length} characters"
            )
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationAppError("Password must contain letters and numbers")
