"""Application configuration (12-factor via environment)."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve monorepo root `.env` when running from apps/api
_ROOT = Path(__file__).resolve().parents[4]
_ENV_CANDIDATES = (
    _ROOT / ".env",
    Path.cwd() / ".env",
    Path.cwd().parent.parent / ".env",
)
_ENV_FILES = tuple(str(p) for p in _ENV_CANDIDATES if p.is_file()) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Enterprise AI Workspace"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    web_url: str = "http://localhost:3000"
    api_public_url: str = "http://localhost:8000"

    jwt_secret: str = Field(
        default="dev-only-change-me-to-a-long-random-secret-key",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    password_min_length: int = 8

    database_url: str = (
        "postgresql+psycopg://eaw:eaw_secret@localhost:5432/eaw"
    )
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    oauth_redirect_base: str = "http://localhost:8000/api/v1/auth/oauth"

    email_backend: str = "console"
    smtp_from: str = "noreply@enterprise-ai-workspace.local"

    rate_limit_auth_per_minute: int = 20
    rate_limit_api_per_minute: int = 120

    # Object storage
    storage_backend: str = "local"  # local | s3
    local_storage_path: str = "data/uploads"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "eaw-documents"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    max_upload_mb: int = 50

    # Ingestion / RAG (Phase 4)
    ingestion_mode: str = "sync"  # sync | async (Celery)
    embedding_provider: str = "hash"  # hash | openai | sentence_transformers
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    chunk_size: int = 800
    chunk_overlap: int = 120
    qdrant_collection: str = "eaw_chunks"
    vector_store_backend: str = "memory"  # memory | qdrant
    celery_task_always_eager: bool = False

    # Chat / RAG generation (Phase 5)
    llm_provider: str = "echo"  # echo | openai
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    rag_top_k: int = 20
    rag_rerank_top_n: int = 6
    rag_min_score: float = 0.15
    rag_max_context_chars: int = 12000
    chat_history_turns: int = 8
    chat_memory_threshold_messages: int = 12

    # GitHub connector (Phase 6)
    github_api_base: str = "https://api.github.com"
    github_sync_max_files: int = 80
    github_sync_max_file_bytes: int = 200_000

    # Notion / Google Drive (Phase 7)
    notion_api_base: str = "https://api.notion.com"
    notion_api_version: str = "2022-06-28"
    notion_sync_max_pages: int = 50
    gdrive_api_base: str = "https://www.googleapis.com"
    gdrive_sync_max_files: int = 50
    gdrive_sync_max_file_bytes: int = 2_000_000

    # Slack / Jira (Phase 8)
    slack_api_base: str = "https://slack.com/api"
    slack_sync_max_messages: int = 200
    jira_sync_max_issues: int = 100

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def github_oauth_enabled(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> object:
        """Render/Heroku give postgres:// or postgresql:// — SQLAlchemy needs +psycopg."""
        if not isinstance(v, str) or not v:
            return v
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and "+psycopg" not in v.split("://", 1)[0]:
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_not_placeholder_in_prod(cls, v: str) -> str:
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
