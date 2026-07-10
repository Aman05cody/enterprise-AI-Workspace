"""Prometheus text exposition helpers."""

from __future__ import annotations

from eaw import __version__
from eaw.api import middleware as mw


def render_prometheus() -> str:
    lines: list[str] = [
        "# HELP eaw_info Application info",
        "# TYPE eaw_info gauge",
        f'eaw_info{{version="{__version__}"}} 1',
    ]
    inst = mw.metrics_middleware_instance
    if inst is None:
        lines.append("# HELP eaw_http_requests_total Total HTTP requests")
        lines.append("# TYPE eaw_http_requests_total counter")
        lines.append("eaw_http_requests_total 0")
        return "\n".join(lines) + "\n"

    with inst._lock:
        req = inst.request_count
        err = inst.error_count
        latency = inst.total_latency_ms
        by_status = dict(inst.by_status)

    lines.extend(
        [
            "# HELP eaw_http_requests_total Total HTTP requests",
            "# TYPE eaw_http_requests_total counter",
            f"eaw_http_requests_total {req}",
            "# HELP eaw_http_errors_total HTTP 5xx responses",
            "# TYPE eaw_http_errors_total counter",
            f"eaw_http_errors_total {err}",
            "# HELP eaw_http_latency_ms_sum Cumulative request latency in ms",
            "# TYPE eaw_http_latency_ms_sum counter",
            f"eaw_http_latency_ms_sum {latency}",
            "# HELP eaw_http_responses_total Responses by status code",
            "# TYPE eaw_http_responses_total counter",
        ]
    )
    for code, count in sorted(by_status.items()):
        lines.append(f'eaw_http_responses_total{{status="{code}"}} {count}')

    # Queue snapshot (best-effort; skip if DB unavailable / slow)
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        from eaw.application.services.monitoring_service import MonitoringService
        from eaw.core.config import get_settings

        settings = get_settings()
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 1},
            pool_size=1,
            max_overflow=0,
        )
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            db.execute(text("SELECT 1"))
            snap = MonitoringService(db, settings).snapshot()
            queues = snap.get("queues") or {}
            lines.append("# HELP eaw_documents_pending Documents pending ingestion")
            lines.append("# TYPE eaw_documents_pending gauge")
            lines.append(
                f"eaw_documents_pending {int(queues.get('documents_pending') or 0)}"
            )
            lines.append("# HELP eaw_ingestion_jobs_active Active ingestion jobs")
            lines.append("# TYPE eaw_ingestion_jobs_active gauge")
            lines.append(
                f"eaw_ingestion_jobs_active {int(queues.get('ingestion_jobs_active') or 0)}"
            )
        finally:
            db.close()
            engine.dispose()
    except Exception:  # noqa: BLE001
        pass

    return "\n".join(lines) + "\n"
