# Phase 2 Completion Report

| Field | Value |
|-------|--------|
| Phase | 2 — Foundation |
| Status | Complete |
| Date | 2026-07-11 |

## Delivered

### Infrastructure
- Monorepo root with `.env.example`, Docker Compose, Makefile
- Services defined: Postgres, Redis, Qdrant, MinIO, API, Web
- API Dockerfile + Web Dockerfile

### Backend (`apps/api`)
- Clean Architecture packages: `domain`, `application`, `infrastructure`, `api`, `core`
- SQLAlchemy models: users, oauth_accounts, refresh_tokens, email/password tokens, organizations, memberships, departments, invites, audit_logs
- Alembic migration `20260711_0001`
- Auth service: register, login, refresh rotation, logout, profile, email verify, password reset
- Org service: workspaces, members, roles, invites, departments
- RBAC: owner / admin / manager / employee / guest
- OpenAPI via FastAPI `/docs`
- Celery app stub for Phase 4
- Unit tests: security + RBAC (6 passing)

### Frontend (`apps/web`)
- Next.js 15 + React 19 + TypeScript + Tailwind
- Landing, login, register, dashboard
- Axios client with token refresh interceptor
- TanStack Query + React Hook Form + Zod
- shadcn-style UI primitives

## Design decisions (Phase 2)

1. **Refresh tokens hashed at rest** (SHA-256); raw token only returned once.
2. **Last-owner protection** on demote/remove.
3. **Invite raw token returned in API response** for local/dev convenience (email is console-logged); production should rely on email only.
4. **OAuth routes scaffolded** — full redirect flow activates when client IDs/secrets are set (implementation completed for status checks; full OAuth exchange can be expanded when credentials exist).
5. **Modular monolith** preserved for later document/RAG modules.

## How to run

See root `README.md`. Requires Docker (or local Postgres matching `DATABASE_URL`) for full API runtime.

```bash
# Unit tests (no DB)
cd apps/api && .venv\Scripts\python -m pytest tests -q

# With Docker
docker compose up --build
```

## Explicitly out of Phase 2

- Document upload / S3 wiring (Phase 3)
- Chunking / embeddings / Qdrant index (Phase 4)
- Chat / RAG (Phase 5)
- Full Google/GitHub OAuth redirect completion when credentials provided (hooks ready)

## Stop gate

Wait for **NEXT PHASE** before Phase 3.
