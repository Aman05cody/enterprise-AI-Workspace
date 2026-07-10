# 5. System Architecture

| Field | Value |
|-------|--------|
| Document ID | EAW-ARCH-001 |
| Version | 1.0.0 |
| Style | Clean Architecture · Modular Monolith · Ports & Adapters |

---

## 5.1 Architectural Goals

1. **Multi-tenant safety** — workspace isolation non-negotiable  
2. **Grounded AI** — retrieval → rerank → compress → generate → cite  
3. **Modular growth** — connectors plug in without rewriting core  
4. **Operability** — Docker, workers, health, audit, metrics  
5. **Swap-friendly AI** — provider abstraction for LLMs/embeddings  
6. **Enterprise UX** — dense, trustworthy, citation-first interface  

---

## 5.2 Style Decision

| Option | Decision | Why |
|--------|----------|-----|
| Microservices day-1 | Rejected | Ops cost; premature for single product team |
| Modular monolith API | **Selected** | Clear modules; one deployable; extract later |
| Separate BFF | Deferred | Next.js → FastAPI direct for v1 |
| Event bus (Kafka) | Deferred | Redis/Celery sufficient initially |

---

## 5.3 Logical Layers

```
┌─────────────────────────────────────────────┐
│ Presentation (Next.js 15 / React 19)        │
│ Features · Shared UI · TanStack Query       │
└──────────────────┬──────────────────────────┘
                   │ HTTPS / JWT / SSE
┌──────────────────▼──────────────────────────┐
│ API Adapters (FastAPI)                      │
│ Routers · Pydantic DTOs · Middleware · DI   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Application (Use Cases / Services)          │
│ Auth · Org · Docs · Ingestion · Chat · ...  │
│ Ports: LLM, Embeddings, Vector, Storage,    │
│        Connector, OCR, VirusScan, Email     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Domain                                      │
│ Entities · Enums · Policies (RBAC, Grounding)│
└──────────────────┬──────────────────────────┘
                   │ implemented by
┌──────────────────▼──────────────────────────┐
│ Infrastructure                              │
│ SQLAlchemy · Alembic · Redis · Celery       │
│ Qdrant · S3 · OAuth · LLM providers         │
│ LangChain/LlamaIndex adapters · Connectors  │
└─────────────────────────────────────────────┘
```

### SOLID Application

| Principle | Practice |
|-----------|----------|
| S | One service per use-case cluster |
| O | New connectors/providers as adapters |
| L | Providers honor shared port contracts |
| I | Separate ports (chat ≠ embeddings ≠ storage) |
| D | Application depends on ports only |

---

## 5.4 Bounded Contexts (Modules)

| Module | Responsibility |
|--------|----------------|
| **Identity** | Users, passwords, OAuth, tokens, verification, reset |
| **Tenancy** | Workspaces, memberships, invites, departments, settings |
| **Access** | RBAC policies, department scopes |
| **Knowledge** | Knowledge bases, documents, versions, metadata |
| **Ingestion** | Pipeline orchestration, jobs, OCR hooks |
| **Retrieval** | Hybrid search, rerank, compression |
| **Conversation** | Chats, messages, citations, memory, feedback |
| **Connectors** | GitHub, Notion, Drive, Slack, Jira (phased) |
| **Analytics** | Usage events, aggregations |
| **Audit** | Security/admin event log |
| **BillingReady** | Plan/seat/usage hooks (no full payments required in early phases) |
| **Platform** | Health, config, feature flags |

---

## 5.5 Multi-Tenancy Model

| Aspect | Design |
|--------|--------|
| Model | Shared DB + shared schema + **row-level** `organization_id` |
| Vectors | Payload filter: `organization_id` + `knowledge_base_id` / `source_id` |
| Storage keys | `{org_id}/...` prefix |
| Enforcement | Membership + server filters (never trust client alone) |
| Departments | Optional secondary scope on resources |

---

## 5.6 Sync vs Async

| Synchronous (API request) | Asynchronous (Celery) |
|---------------------------|------------------------|
| Auth, RBAC, CRUD | Document extract/chunk/embed |
| Chat orchestration + stream proxy | OCR |
| Search | Connector full/incremental sync |
| Analytics queries | Cleanup, reindex, summaries batch |

---

## 5.7 AI Core (Summary)

```
Query
  → AuthZ + rate limit
  → Hybrid retrieve (Qdrant + filters)
  → Cross-encoder rerank
  → Context compression
  → Prompt template (grounding + cite)
  → LLM (stream)
  → Confidence + citations
  → Persist message/usage
```

**Grounding policy** lives in domain/application, not only in prompts.

---

## 5.8 Connector Architecture (Future-Proof)

```
ConnectorPort
  - connect(oauth)
  - list_resources()
  - sync(resource_ids)
  - webhook/handle_event()  # optional

Each connector produces NormalizedSourceDocuments
  → same ingestion pipeline as uploads
```

GitHub may add specialized tools (PR review) as **tool-using skills** on top of indexed code + live API calls.

---

## 5.9 Frontend Architecture

| Layer | Role |
|-------|------|
| `app/` | Routes, layouts |
| `features/` | auth, workspace, knowledge, chat, connectors, analytics |
| `entities/` | Domain types |
| `widgets/` | Shell, sidebar, citation panel |
| `shared/ui` | shadcn components |
| `shared/api` | Axios + interceptors + React Query |

---

## 5.10 Cross-Cutting

| Concern | Approach |
|---------|----------|
| Config | Pydantic Settings / env |
| Logging | Structured + correlation IDs |
| Errors | Stable error codes + safe messages |
| Validation | Pydantic + Zod |
| Caching | Redis (rate limit, optional semantic cache later) |
| Security | JWT, RBAC, headers, audit |

---

## 5.11 Key ADRs (Binding)

| ID | Decision |
|----|----------|
| ADR-001 | Modular monolith for v1 |
| ADR-002 | Row-level multi-tenancy |
| ADR-003 | Celery for async AI/indexing |
| ADR-004 | Qdrant vector DB |
| ADR-005 | LLM provider abstraction |
| ADR-006 | SSE for streaming chat |
| ADR-007 | Hybrid retrieval + cross-encoder + compression |
| ADR-008 | Refuse-on-insufficient-context default |
| ADR-009 | Connectors share normalized ingestion pipeline |
| ADR-010 | S3-compatible object storage only (no DB BLOBs) |

---

**Next:** [../diagrams/06-ARCHITECTURE-DIAGRAMS.md](../diagrams/06-ARCHITECTURE-DIAGRAMS.md)
