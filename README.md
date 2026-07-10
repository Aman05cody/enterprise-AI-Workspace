# Enterprise AI Workspace

Production-oriented multi-tenant **Enterprise AI Workspace** — knowledge management, grounded RAG chat, connectors, and admin analytics.

| Phase | Status |
|-------|--------|
| 1 Planning | ✅ |
| 2 Foundation / Auth / RBAC | ✅ |
| 3 Document management | ✅ |
| 4 RAG indexing | ✅ |
| 5 Enterprise chat | ✅ |
| 6 GitHub intelligence | ✅ |
| 7 Notion + Google Drive | ✅ |
| 8 Slack + Jira | ✅ |
| 9 Admin analytics | ✅ |
| 10 Testing / CI / Deploy | ✅ |
| **11 Production hardening+** | ✅ **Complete** |

**Version:** `1.1.0`

---

## Quick start (local)

```bash
cp .env.example .env
# optional: docker compose up -d postgres redis qdrant

cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
set PYTHONPATH=src
alembic upgrade head
uvicorn eaw.main:app --reload --port 8000

cd ../web
npm ci
set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

- Web: http://localhost:3000  
- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  
- Metrics: http://localhost:8000/metrics  

Seed demo: `python -m scripts.seed` → `owner@example.com` / `Owner123!`

---

## Deploy on Render (public URL)

See **[docs/RENDER.md](./docs/RENDER.md)** and root `render.yaml`.

```powershell
# 1) Login to GitHub, push repo
powershell -ExecutionPolicy Bypass -File scripts\push-and-deploy-render.ps1

# 2) In browser: Render → New → Blueprint → connect repo → Apply
```

## Production (Docker / VPS)

See **[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)**.

```bash
cp .env.example .env.prod
# set strong secrets
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Security checklist: **[docs/SECURITY.md](./docs/SECURITY.md)**  
Architecture & planning: **[docs/README.md](./docs/README.md)**

---

## Stack

| Layer | Tech |
|-------|------|
| Web | Next.js 15, React 19, Tailwind, TanStack Query, Recharts |
| API | FastAPI, SQLAlchemy, Alembic, Celery |
| Data | PostgreSQL, Redis, Qdrant, local/S3 storage |
| AI | Provider-abstracted embeddings/LLM, hybrid retrieval, grounded chat |
| Ops | Docker multi-stage, Nginx, GitHub Actions CI |

---

## Product modules

- Multi-tenant workspaces + RBAC + departments  
- Knowledge bases, upload, versioning, preview  
- Async/sync ingestion → chunks → embeddings → vectors  
- Streaming chat with citations + refuse-on-weak-context  
- Connectors: GitHub, Notion, Drive, Slack, Jira  
- Analytics dashboard + audit + `/metrics`  

---

## CI

GitHub Actions (`.github/workflows/ci.yml`):

1. API Ruff + unit/smoke tests  
2. API **integration tests** (Postgres service)  
3. Web `tsc` + `next build`  
4. Dependency audit (pip-audit / npm audit)  
5. Docker image smoke builds  

Prometheus metrics: `GET /metrics/prometheus`  
Operator JSON metrics: `GET /metrics`

---

## Phase 11 notes

- Dependabot weekly updates  
- Rate limiting middleware on API/auth  
- TLS Nginx example: `infra/nginx/conf.d/tls.example.conf`  

---

## License

Proprietary / internal use unless otherwise licensed.
