"""Database engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eaw.core.config import get_settings

settings = get_settings()
_url = settings.database_url

if _url.startswith("sqlite"):
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        _url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables for local SQLite (Alembic stays Postgres-oriented for prod)."""
    if not settings.database_url.startswith("sqlite"):
        return
    from eaw.infrastructure.db.base import Base
    from eaw.infrastructure.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
