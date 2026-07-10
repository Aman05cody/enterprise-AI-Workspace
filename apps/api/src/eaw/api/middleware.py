"""HTTP middleware."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from eaw.core.config import get_settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time-Ms"] = str(
            int((time.perf_counter() - started) * 1000)
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding-window rate limiter by client IP.
    Suitable for single-instance / edge-complemented deployments.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _limit_for_path(self, path: str) -> int:
        settings = get_settings()
        if path.startswith("/api/v1/auth/"):
            return max(1, settings.rate_limit_auth_per_minute)
        if path.startswith("/api/"):
            return max(1, settings.rate_limit_api_per_minute)
        return 0  # unlimited for non-api

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = self._limit_for_path(request.url.path)
        if limit <= 0:
            return await call_next(request)

        ip = self._client_ip(request)
        key = f"{ip}:{request.url.path.split('/')[1:4]}"  # coarse bucket
        now = time.time()
        window = 60.0

        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Too many requests. Please retry later.",
                            "details": {"limit_per_minute": limit},
                        },
                        "meta": {"request_id": request_id},
                    },
                    headers={"Retry-After": "60"},
                )
            q.append(now)

        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect lightweight request counters for Prometheus export."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_latency_ms = 0
        self._lock = Lock()
        # path prefix -> count
        self.by_status: dict[int, int] = defaultdict(int)

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        latency = int((time.perf_counter() - started) * 1000)
        with self._lock:
            self.request_count += 1
            self.total_latency_ms += latency
            self.by_status[response.status_code] += 1
            if response.status_code >= 500:
                self.error_count += 1
        return response


# Process-wide metrics instance attached in main
metrics_middleware_instance: MetricsMiddleware | None = None
