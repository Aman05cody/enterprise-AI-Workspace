# Deployment Guide — Enterprise AI Workspace

| Field | Value |
|-------|--------|
| Document ID | EAW-DEPLOY-001 |
| Version | 1.0.0 |
| Phase | 10 |

---

## 1. Environments

| Env | Purpose |
|-----|---------|
| local | `docker-compose.yml` (dev reload) |
| staging / production | `docker-compose.prod.yml` + Nginx |

---

## 2. Prerequisites

- Docker Engine 24+ and Docker Compose v2  
- Strong secrets for production (JWT, DB password, provider keys)  
- DNS pointing to host (optional TLS via certbot / load balancer)  

---

## 3. Production quick start

```bash
# 1. Create production env
cp .env.example .env.prod
# Edit .env.prod — set strong JWT_SECRET, POSTGRES_PASSWORD, CORS_ORIGINS, PUBLIC_API_URL

# 2. Build and start
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 3. Check health
curl http://localhost/health
curl http://localhost/metrics
curl http://localhost/metrics/prometheus
curl http://localhost/api/v1/version
```

### TLS

See `infra/nginx/conf.d/tls.example.conf` for HTTPS + HSTS + restricted metrics.
Mount certificates at `/etc/nginx/certs/` and swap the server block.


### Required `.env.prod` keys

```env
POSTGRES_USER=eaw
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=eaw
JWT_SECRET=<at-least-32-random-chars>
CORS_ORIGINS=https://app.example.com
PUBLIC_API_URL=https://app.example.com
WEB_URL=https://app.example.com
APP_ENV=production
APP_DEBUG=false
INGESTION_MODE=async
VECTOR_STORE_BACKEND=qdrant
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=/data/uploads
LLM_PROVIDER=openai
OPENAI_API_KEY=...
EMBEDDING_PROVIDER=openai
```

---

## 4. Architecture (prod compose)

```
Internet → Nginx:80
            ├─ /          → web (Next.js standalone)
            ├─ /api       → api (FastAPI, 2 workers)
            ├─ /health    → api
            └─ /metrics   → api
api/worker → postgres, redis, qdrant, uploads volume
```

---

## 5. Migrations

Run automatically on API container start:

```bash
alembic upgrade head
```

Manual:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 6. Scaling

| Component | Scale approach |
|-----------|----------------|
| API | Increase `uvicorn --workers` or replica count (stateless) |
| Worker | `docker compose up -d --scale worker=3` |
| Redis / Postgres | Managed services recommended for HA |
| Qdrant | Dedicated host/cluster for large corpora |

---

## 7. Backups

1. **PostgreSQL**: daily `pg_dump` of the `eaw` database  
2. **Uploads volume**: snapshot `eaw_uploads`  
3. **Qdrant**: snapshot collection storage volume  
4. Test restore quarterly  

---

## 8. TLS

Recommended options:

1. Terminate TLS at a cloud load balancer / Cloudflare  
2. Or add certbot certificates to Nginx (`listen 443 ssl`)  

Enable HSTS only after HTTPS is verified.

---

## 9. CI/CD

| Workflow | File | Trigger |
|----------|------|---------|
| CI | `.github/workflows/ci.yml` | PR / push |
| CD | `.github/workflows/cd.yml` | Manual dispatch |

CI runs: Ruff + Pytest, Next typecheck/build, Docker image smoke builds.

---

## 10. Local development (recap)

```bash
# Infra only
docker compose up -d postgres redis qdrant

# API
cd apps/api && python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
set PYTHONPATH=src
alembic upgrade head
uvicorn eaw.main:app --reload --port 8000

# Web
cd apps/web && npm ci && npm run dev
```

---

## 11. Smoke checklist after deploy

- [ ] `/health` returns ok  
- [ ] `/ready` postgres ok  
- [ ] Register / login works  
- [ ] Create workspace + knowledge base  
- [ ] Upload document → status becomes ready  
- [ ] Chat returns grounded answer or insufficient-context  
- [ ] `/metrics` shows queues  
- [ ] Analytics page loads for admin  
