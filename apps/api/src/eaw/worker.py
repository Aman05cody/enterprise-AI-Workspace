"""Celery application and task registration."""

from celery import Celery

from eaw.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "eaw",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.celery_task_always_eager,
)


@celery_app.task(name="eaw.ping")
def ping() -> str:
    return "pong"


@celery_app.task(
    name="eaw.ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def ingest_document_task(self, job_id: str) -> dict:
    from eaw.infrastructure.queue.tasks.ingestion import run_ingest_document

    try:
        result = run_ingest_document(job_id)
        if result.get("status") == "failed":
            # Do not auto-retry permanent extract failures endlessly
            err = (result.get("error_message") or "").lower()
            transient = any(
                x in err for x in ("timeout", "connection", "temporarily", "rate")
            )
            if transient:
                raise self.retry(exc=RuntimeError(result.get("error_message")))
        return result
    except self.MaxRetriesExceededError:
        return {"job_id": job_id, "status": "failed", "error": "max retries exceeded"}


@celery_app.task(name="eaw.github_sync", bind=True, max_retries=2, default_retry_delay=60)
def github_sync_task(self, job_id: str) -> dict:
    from eaw.infrastructure.queue.tasks.github_sync import run_github_sync

    try:
        return run_github_sync(job_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@celery_app.task(name="eaw.notion_sync", bind=True, max_retries=2, default_retry_delay=60)
def notion_sync_task(self, job_id: str) -> dict:
    from eaw.infrastructure.queue.tasks.connector_sync import run_notion_sync

    try:
        return run_notion_sync(job_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@celery_app.task(name="eaw.gdrive_sync", bind=True, max_retries=2, default_retry_delay=60)
def gdrive_sync_task(self, job_id: str) -> dict:
    from eaw.infrastructure.queue.tasks.connector_sync import run_gdrive_sync

    try:
        return run_gdrive_sync(job_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@celery_app.task(name="eaw.slack_sync", bind=True, max_retries=2, default_retry_delay=60)
def slack_sync_task(self, job_id: str) -> dict:
    from eaw.infrastructure.queue.tasks.connector_sync import run_slack_sync

    try:
        return run_slack_sync(job_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@celery_app.task(name="eaw.jira_sync", bind=True, max_retries=2, default_retry_delay=60)
def jira_sync_task(self, job_id: str) -> dict:
    from eaw.infrastructure.queue.tasks.connector_sync import run_jira_sync

    try:
        return run_jira_sync(job_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)

