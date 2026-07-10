# Enterprise AI Workspace

Production-oriented multi-tenant **Enterprise AI Workspace** — knowledge management, grounded RAG chat, connectors, and admin analytics.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-eaw--web.vercel.app-black?style=for-the-badge&logo=vercel)](https://eaw-web.vercel.app)
[![API](https://img.shields.io/badge/API-eaw--api.vercel.app-blue?style=for-the-badge&logo=fastapi)](https://eaw-api.vercel.app/docs)
[![Health](https://img.shields.io/badge/Health-ok-success?style=for-the-badge)](https://eaw-api.vercel.app/health)

## 🌐 Live demo

| | URL |
|--|-----|
| **Web app** | **[https://eaw-web.vercel.app](https://eaw-web.vercel.app)** |
| **API** | [https://eaw-api.vercel.app](https://eaw-api.vercel.app) |
| **API docs (Swagger)** | [https://eaw-api.vercel.app/docs](https://eaw-api.vercel.app/docs) |
| **Health check** | [https://eaw-api.vercel.app/health](https://eaw-api.vercel.app/health) |

**Try it:** open the web app → **Register** (password ≥ 8 chars, letters + numbers) → create a workspace.

> Free Vercel hobby deploy. First load can be slow (cold start). Demo AI uses echo/hash providers (no paid OpenAI key required). SQLite data may reset on cold starts.

More deploy notes: **[docs/VERCEL.md](./docs/VERCEL.md)** · **[DEMO.md](./DEMO.md)**

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

## Deploy free on Vercel (recommended)

No paid hosting. See **[docs/VERCEL.md](./docs/VERCEL.md)**.

1. https://vercel.com/signup (GitHub)  
2. Import this repo **twice**:
   - Project 1 root: `apps/api`  
   - Project 2 root: `apps/web` + env `NEXT_PUBLIC_API_URL=<api-url>`  
3. Open the web URL and register  

(Older Render notes: [docs/RENDER.md](./docs/RENDER.md) — optional.)

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

## License

Proprietary / internal use unless otherwise licensed.
