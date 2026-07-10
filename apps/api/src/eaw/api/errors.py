"""Exception handlers."""

import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from eaw.domain.common.errors import AppError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get(
        "X-Request-Id", str(uuid4())
    )


def error_body(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
    status_code: int = 400,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "meta": {"request_id": request_id},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return error_body(
            code=exc.code,
            message=exc.message,
            request_id=_request_id(request),
            details=exc.details,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_body(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            request_id=_request_id(request),
            details={"errors": exc.errors()},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return error_body(
            code="HTTP_ERROR",
            message=str(exc.detail),
            request_id=_request_id(request),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return error_body(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            request_id=_request_id(request),
            status_code=500,
        )
