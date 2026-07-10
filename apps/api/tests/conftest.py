"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure test-friendly defaults before app import
os.environ.setdefault(
    "JWT_SECRET", "ci-only-change-me-to-a-long-random-secret-key"
)
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("INGESTION_MODE", "sync")
os.environ.setdefault("EMBEDDING_PROVIDER", "hash")
os.environ.setdefault("VECTOR_STORE_BACKEND", "memory")
os.environ.setdefault("LLM_PROVIDER", "echo")
os.environ.setdefault("STORAGE_BACKEND", "local")

# Prefer dedicated test DB URL when present
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


def _database_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")


def postgres_available() -> bool:
    url = _database_url()
    if not url or "postgres" not in url:
        return False
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="session")
def pg_engine():
    if not postgres_available():
        pytest.skip("PostgreSQL not available for integration tests")
    from eaw.infrastructure.db.base import Base
    from eaw.infrastructure.db import models  # noqa: F401
    from eaw.infrastructure.db import session as db_session

    url = _database_url()
    assert url
    engine = create_engine(url, pool_pre_ping=True)
    # Rebind global SessionLocal so Celery-sync ingestion hits the same DB
    db_session.engine = engine
    db_session.SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    from eaw.infrastructure.db import session as db_session

    session = db_session.SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def api_client(pg_engine, tmp_path, monkeypatch):
    """TestClient with DB override and temp local storage."""
    from eaw.core.config import get_settings
    from eaw.infrastructure.db.session import get_db
    from eaw.infrastructure.db import session as db_session
    from eaw.infrastructure.storage.factory import get_object_storage
    from eaw.infrastructure.storage.local import LocalObjectStorage
    from eaw.main import app

    get_settings.cache_clear()
    get_object_storage.cache_clear()
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    get_object_storage.cache_clear()

    store = LocalObjectStorage(tmp_path / "uploads")

    def _override_db():
        db = db_session.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    monkeypatch.setattr("eaw.api.deps.get_object_storage", lambda: store)
    monkeypatch.setattr(
        "eaw.infrastructure.storage.factory.get_object_storage", lambda: store
    )
    monkeypatch.setattr(
        "eaw.application.services.document_service.get_object_storage",
        lambda: store,
        raising=False,
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_object_storage.cache_clear()
