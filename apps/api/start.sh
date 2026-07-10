#!/usr/bin/env bash
# Render / container entrypoint for the API
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
export PYTHONUNBUFFERED=1
mkdir -p /tmp/eaw-uploads

# SQLite (free demo): create tables via SQLAlchemy — skip Alembic (Postgres-oriented)
# Postgres: run Alembic migrations
if [[ "${DATABASE_URL:-}" == sqlite* ]]; then
  echo "→ SQLite mode: creating tables…"
  python -c "from eaw.infrastructure.db.session import init_db; init_db(); print('tables ready')"
else
  echo "→ Running Alembic migrations…"
  alembic upgrade head
fi

PORT="${PORT:-8000}"
echo "→ Starting API on 0.0.0.0:${PORT}"
# Single worker: free-tier memory/SQLite are process-local
exec uvicorn eaw.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
