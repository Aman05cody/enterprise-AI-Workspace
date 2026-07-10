"""Enqueue ingestion jobs (sync or Celery async)."""

from __future__ import annotations

import logging
from uuid import UUID

from eaw.core.config import get_settings

logger = logging.getLogger(__name__)


def enqueue_ingestion_job(job_id: UUID) -> str | None:
    """
    Dispatch ingestion job.
    Returns celery task id when async; None when sync completed/inline.
    """
    settings = get_settings()
    mode = (settings.ingestion_mode or "sync").lower()

    if mode == "async" or settings.celery_task_always_eager:
        try:
            from eaw.worker import ingest_document_task

            async_result = ingest_document_task.delay(str(job_id))
            logger.info("Enqueued celery ingest job=%s task=%s", job_id, async_result.id)
            return async_result.id
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Celery enqueue failed (%s); falling back to sync for job=%s",
                exc,
                job_id,
            )

    # Sync path — run in-process (also used when Redis unavailable)
    from eaw.infrastructure.queue.tasks.ingestion import run_ingest_document

    logger.info("Running ingestion synchronously job=%s", job_id)
    run_ingest_document(str(job_id))
    return None


def enqueue_github_sync(job_id: UUID) -> str | None:
    """Dispatch GitHub connector sync job."""
    settings = get_settings()
    mode = (settings.ingestion_mode or "sync").lower()
    if mode == "async" or settings.celery_task_always_eager:
        try:
            from eaw.worker import github_sync_task

            async_result = github_sync_task.delay(str(job_id))
            logger.info("Enqueued github sync job=%s task=%s", job_id, async_result.id)
            return async_result.id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Celery github sync enqueue failed: %s", exc)

    from eaw.infrastructure.queue.tasks.github_sync import run_github_sync

    run_github_sync(str(job_id))
    return None


def enqueue_notion_sync(job_id: UUID) -> str | None:
    settings = get_settings()
    mode = (settings.ingestion_mode or "sync").lower()
    if mode == "async" or settings.celery_task_always_eager:
        try:
            from eaw.worker import notion_sync_task

            async_result = notion_sync_task.delay(str(job_id))
            return async_result.id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Celery notion sync enqueue failed: %s", exc)
    from eaw.infrastructure.queue.tasks.connector_sync import run_notion_sync

    run_notion_sync(str(job_id))
    return None


def enqueue_gdrive_sync(job_id: UUID) -> str | None:
    settings = get_settings()
    mode = (settings.ingestion_mode or "sync").lower()
    if mode == "async" or settings.celery_task_always_eager:
        try:
            from eaw.worker import gdrive_sync_task

            async_result = gdrive_sync_task.delay(str(job_id))
            return async_result.id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Celery gdrive sync enqueue failed: %s", exc)
    from eaw.infrastructure.queue.tasks.connector_sync import run_gdrive_sync

    run_gdrive_sync(str(job_id))
    return None


def enqueue_slack_sync(job_id: UUID) -> str | None:
    settings = get_settings()
    mode = (settings.ingestion_mode or "sync").lower()
    if mode == "async" or settings.celery_task_always_eager:
        try:
            from eaw.worker import slack_sync_task

            async_result = slack_sync_task.delay(str(job_id))
            return async_result.id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Celery slack sync enqueue failed: %s", exc)
    from eaw.infrastructure.queue.tasks.connector_sync import run_slack_sync

    run_slack_sync(str(job_id))
    return None


def enqueue_jira_sync(job_id: UUID) -> str | None:
    settings = get_settings()
    mode = (settings.ingestion_mode or "sync").lower()
    if mode == "async" or settings.celery_task_always_eager:
        try:
            from eaw.worker import jira_sync_task

            async_result = jira_sync_task.delay(str(job_id))
            return async_result.id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Celery jira sync enqueue failed: %s", exc)
    from eaw.infrastructure.queue.tasks.connector_sync import run_jira_sync

    run_jira_sync(str(job_id))
    return None
