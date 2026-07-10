"""Domain and application errors."""


class AppError(Exception):
    """Base application error mapped to HTTP by the API layer."""

    code: str = "APP_ERROR"
    status_code: int = 400

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422
