"""Health, readiness, and monitoring endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from eaw import __version__
from eaw.api.deps import MonitoringSvc
from eaw.api.schemas.common import DataResponse, Meta
from eaw.core.config import get_settings
from eaw.infrastructure.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"error: {exc}"
        return {"status": "degraded", "checks": checks}
    return {"status": "ok", "checks": checks}


@router.get("/metrics")
def metrics(mon: MonitoringSvc) -> dict:
    """Operator monitoring snapshot (queues, dependency checks, config)."""
    return mon.snapshot()


@router.get(f"{get_settings().api_prefix}/version")
def version() -> DataResponse[dict]:
    settings = get_settings()
    return DataResponse(
        data={
            "name": settings.app_name,
            "version": __version__,
            "env": settings.app_env,
            "phase": 11,
        },
        meta=Meta(),
    )
