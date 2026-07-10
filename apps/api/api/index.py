"""Vercel serverless entrypoint — re-exports the FastAPI app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure `src/` is on PYTHONPATH for `import eaw`
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Free demo defaults when env not set in Vercel dashboard
os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault(
    "JWT_SECRET",
    os.environ.get("JWT_SECRET", "vercel-demo-change-me-to-a-long-random-secret"),
)
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/eaw.db")
os.environ.setdefault("INGESTION_MODE", "sync")
os.environ.setdefault("EMBEDDING_PROVIDER", "hash")
os.environ.setdefault("VECTOR_STORE_BACKEND", "memory")
os.environ.setdefault("LLM_PROVIDER", "echo")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("LOCAL_STORAGE_PATH", "/tmp/eaw-uploads")

from eaw.main import app  # noqa: E402, F401
