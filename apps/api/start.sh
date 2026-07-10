#!/usr/bin/env bash
# Render / container entrypoint for the API
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"
export PYTHONUNBUFFERED=1

echo "→ Running database migrations…"
alembic upgrade head

PORT="${PORT:-8000}"
echo "→ Starting API on 0.0.0.0:${PORT}"
# Single worker: free-tier memory vector store is process-local
exec uvicorn eaw.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
