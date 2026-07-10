"""FastAPI application entrypoint."""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from eaw import __version__
from eaw.api import middleware as mw
from eaw.api.errors import register_exception_handlers
from eaw.api.middleware import RateLimitMiddleware, RequestIdMiddleware
from eaw.api.prometheus import render_prometheus
from eaw.api.v1.health import router as health_router
from eaw.api.v1.router import api_router
from eaw.core.config import get_settings
from eaw.core.logging import setup_logging


class _MetricsState:
    def __init__(self) -> None:
        self.request_count = 0
        self.error_count = 0
        self.total_latency_ms = 0
        self.by_status: dict[int, int] = defaultdict(int)
        self._lock = Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Enterprise AI Workspace API — multi-tenant knowledge & RAG platform. "
            "Production-ready modular monolith (Phases 1–11)."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # Allow Render preview/production frontends without hardcoding hostnames
        allow_origin_regex=r"https://.*\.onrender\.com",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Process-Time-Ms", "Retry-After"],
    )
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(RequestIdMiddleware)

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router, prefix=settings.api_prefix)

    # Process metrics (single shared state)
    mw.metrics_middleware_instance = _MetricsState()  # type: ignore[assignment]

    @application.middleware("http")
    async def metrics_http_middleware(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        latency = int((time.perf_counter() - started) * 1000)
        inst = mw.metrics_middleware_instance
        if inst is not None:
            with inst._lock:  # type: ignore[union-attr]
                inst.request_count += 1  # type: ignore[union-attr]
                inst.total_latency_ms += latency  # type: ignore[union-attr]
                inst.by_status[response.status_code] += 1  # type: ignore[union-attr]
                if response.status_code >= 500:
                    inst.error_count += 1  # type: ignore[union-attr]
        return response

    @application.get(
        "/metrics/prometheus",
        response_class=PlainTextResponse,
        tags=["health"],
    )
    def prometheus_metrics() -> str:
        return render_prometheus()

    return application


app = create_app()
