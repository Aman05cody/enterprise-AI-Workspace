# 14. Tech Stack Justification

| Field | Value |
|-------|--------|
| Document ID | EAW-TECH-001 |
| Version | 1.0.0 |

---

## 14.1 Frontend

| Tech | Why |
|------|-----|
| **Next.js 15** | App Router, SSR/SEO for marketing, solid enterprise SPA patterns, file-based routing |
| **React 19** | Component model maturity; concurrent features for chat UX |
| **TypeScript** | Contract safety across large UI surface |
| **Tailwind CSS** | Fast, consistent design system implementation |
| **shadcn/ui** | Accessible, composable primitives; enterprise look without locked design kit |
| **Framer Motion** | Controlled motion for polished product feel |
| **TanStack Query** | Server-state cache, retries, mutations for REST |
| **React Hook Form + Zod** | Performant forms + shared validation schemas |
| **Recharts** | Admin analytics visualizations |
| **Axios** | Interceptors for auth refresh and org headers |

---

## 14.2 Backend

| Tech | Why |
|------|-----|
| **FastAPI** | High performance async API; native OpenAPI; Pydantic synergy |
| **Python** | Best ecosystem for RAG, OCR, ML utilities |
| **SQLAlchemy** | Mature ORM; multi-tenant query patterns |
| **Alembic** | Controlled schema evolution |
| **Pydantic** | Validation at boundaries; settings management |
| **Redis** | Celery broker, rate limits, cache |
| **Celery** | Battle-tested async jobs for ingestion/sync |

---

## 14.3 AI Stack

| Tech | Why |
|------|-----|
| **LangChain** | Orchestration helpers, tools, prompt plumbing |
| **LlamaIndex** | Strong document loaders/node parsing utilities |
| **OpenAI SDK + abstraction** | Default quality path; swap Grok/Gemini/OpenRouter |
| **Sentence Transformers** | Optional local/open embeddings; cost control profile |
| **Cross-encoder re-ranking** | Material quality boost over pure vector top-k |
| **Qdrant** | Production vector DB; payload filtering for multi-tenant ACL |

**Design rule:** LangChain/LlamaIndex are **infrastructure adapters**, not the domain core.

---

## 14.4 Data & Storage

| Tech | Why |
|------|-----|
| **PostgreSQL** | Relational integrity for tenancy, RBAC, audit, conversations |
| **Qdrant** | Vector search with rich payload filters |
| **S3-compatible** | Durable object storage; MinIO locally; AWS/GCS-S3 in prod |

---

## 14.5 Auth

| Mechanism | Why |
|-----------|-----|
| **JWT access** | Stateless horizontal API scale |
| **Refresh tokens** | UX without long-lived access tokens |
| **Google/GitHub OAuth** | Enterprise/dev-friendly identity |

---

## 14.6 Deployment

| Tech | Why |
|------|-----|
| **Docker + Compose** | Reproducible full stack |
| **Nginx** | TLS, routing, headers, upload limits |
| **GitHub Actions** | Native CI/CD for GitHub-centric teams |

---

## 14.7 Alternatives Considered

| Area | Alternative | Why not (v1) |
|------|-------------|--------------|
| API | Django/NestJS | Heavier or weaker Python AI fit |
| Vectors | Pinecone/Weaviate/pgvector only | Qdrant balance of control + filters; pgvector later optional |
| Queue | RQ/Arq | Celery ecosystem & ops familiarity |
| Frontend | Vite SPA only | Next.js better product shell & routing |
| Monorepo vs polyrepo | Polyrepo | Slower iteration for single product |

---

## 14.8 Alignment to Principles

| Principle | Stack support |
|-----------|---------------|
| Clean Architecture | Ports for LLM/storage/vector/connectors |
| SOLID | Provider factories & interfaces |
| DRY | Shared shadcn + service modules |
| KISS | Modular monolith before microservices |
| Security | JWT, RBAC, validation, headers, audit |

---

**Next:** [../product/15-ROADMAP-TIMELINE.md](../product/15-ROADMAP-TIMELINE.md)
