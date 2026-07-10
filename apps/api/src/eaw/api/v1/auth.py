"""Authentication routes."""

from fastapi import APIRouter, Request

from eaw.api.deps import AppSettings, AuthSvc, CurrentUser, get_client_meta
from eaw.api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    OAuthStatusOut,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    VerifyEmailRequest,
)
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta, UserOut
from eaw.domain.common.errors import ValidationAppError

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_payload(user, access: str, refresh: str, settings) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
        user=UserOut.from_model(user),
    )


@router.post("/register", response_model=DataResponse[TokenResponse], status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    auth: AuthSvc,
    settings: AppSettings,
) -> DataResponse[TokenResponse]:
    ip, ua = get_client_meta(request)
    user, access, refresh = auth.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        ip=ip,
        user_agent=ua,
    )
    rid = getattr(request.state, "request_id", None)
    return DataResponse(
        data=_token_payload(user, access, refresh, settings),
        meta=Meta(request_id=rid),
    )


@router.post("/login", response_model=DataResponse[TokenResponse])
def login(
    body: LoginRequest,
    request: Request,
    auth: AuthSvc,
    settings: AppSettings,
) -> DataResponse[TokenResponse]:
    ip, ua = get_client_meta(request)
    user, access, refresh = auth.login(
        email=body.email, password=body.password, ip=ip, user_agent=ua
    )
    return DataResponse(
        data=_token_payload(user, access, refresh, settings),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/refresh", response_model=DataResponse[TokenResponse])
def refresh(
    body: RefreshRequest,
    request: Request,
    auth: AuthSvc,
    settings: AppSettings,
) -> DataResponse[TokenResponse]:
    ip, ua = get_client_meta(request)
    user, access, refresh_tok = auth.refresh(
        refresh_token=body.refresh_token, ip=ip, user_agent=ua
    )
    return DataResponse(
        data=_token_payload(user, access, refresh_tok, settings),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    body: LogoutRequest,
    request: Request,
    auth: AuthSvc,
    user: CurrentUser,
) -> MessageResponse:
    auth.logout(refresh_token=body.refresh_token, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/me", response_model=DataResponse[UserOut])
def me(request: Request, user: CurrentUser) -> DataResponse[UserOut]:
    return DataResponse(
        data=UserOut.from_model(user),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch("/me", response_model=DataResponse[UserOut])
def update_me(
    body: UpdateProfileRequest,
    request: Request,
    auth: AuthSvc,
    user: CurrentUser,
) -> DataResponse[UserOut]:
    updated = auth.update_profile(
        user.id, full_name=body.full_name, avatar_url=body.avatar_url
    )
    return DataResponse(
        data=UserOut.from_model(updated),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/verify-email", response_model=DataResponse[UserOut])
def verify_email(
    body: VerifyEmailRequest, request: Request, auth: AuthSvc
) -> DataResponse[UserOut]:
    user = auth.verify_email(body.token)
    return DataResponse(
        data=UserOut.from_model(user),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    request: Request, auth: AuthSvc, user: CurrentUser
) -> MessageResponse:
    auth.resend_verification(user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/password/forgot", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordRequest, request: Request, auth: AuthSvc
) -> MessageResponse:
    auth.forgot_password(body.email)
    return MessageResponse(
        data={"ok": True, "message": "If the email exists, a reset link was sent"},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post("/password/reset", response_model=MessageResponse)
def reset_password(
    body: ResetPasswordRequest, request: Request, auth: AuthSvc
) -> MessageResponse:
    auth.reset_password(token=body.token, new_password=body.new_password)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/oauth/status", response_model=DataResponse[OAuthStatusOut])
def oauth_status(request: Request, settings: AppSettings) -> DataResponse[OAuthStatusOut]:
    return DataResponse(
        data=OAuthStatusOut(
            google_enabled=settings.google_oauth_enabled,
            github_enabled=settings.github_oauth_enabled,
        ),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/oauth/google/start")
def google_start(settings: AppSettings) -> None:
    if not settings.google_oauth_enabled:
        raise ValidationAppError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    raise ValidationAppError(
        "Google OAuth start is scaffolded; complete provider app setup to enable redirects."
    )


@router.get("/oauth/github/start")
def github_start(settings: AppSettings) -> None:
    if not settings.github_oauth_enabled:
        raise ValidationAppError(
            "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET."
        )
    raise ValidationAppError(
        "GitHub OAuth start is scaffolded; complete provider app setup to enable redirects."
    )
