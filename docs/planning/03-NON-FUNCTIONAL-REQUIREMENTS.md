# 3. Non-Functional Requirements

| Field | Value |
|-------|--------|
| Document ID | EAW-NFR-001 |
| Version | 1.0.0 |

---

## 3.1 Quality Goals

| Attribute | Goal |
|-----------|------|
| Security | Zero cross-tenant leakage; strong auth; least privilege |
| Reliability | Async resilience; graceful LLM failure handling |
| Performance | Fast CRUD; streaming chat; bounded retrieval latency |
| Scalability | Horizontal workers; stateless API |
| Maintainability | Clean Architecture; modular connectors |
| Observability | Logs, audit, usage metrics |
| Usability | Enterprise-grade UI density and clarity |
| Compliance readiness | Auditability, retention, deletion paths |

---

## 3.2 Performance (PERF)

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-PERF-001 | Non-AI CRUD p95 | ≤ 300 ms |
| NFR-PERF-002 | Auth validate/login platform p95 | ≤ 200 ms |
| NFR-PERF-003 | Upload accept→queued p95 (≤10MB) | ≤ 2 s |
| NFR-PERF-004 | Vector search p95 (top_k=20) | ≤ 250 ms (local network) |
| NFR-PERF-005 | Rerank p95 (≤50 candidates) | ≤ 400 ms (CPU baseline) |
| NFR-PERF-006 | Chat TTFT p95 (stream) | ≤ 3 s + provider |
| NFR-PERF-007 | Full non-stream chat p95 | ≤ 8 s + provider |
| NFR-PERF-008 | Web authenticated shell LCP target | ≤ 2.5 s broadband |

AI provider time is tracked separately from platform overhead.

---

## 3.3 Scalability (SCAL)

| ID | Requirement |
|----|-------------|
| NFR-SCAL-001 | Stateless API instances |
| NFR-SCAL-002 | Celery workers scale horizontally |
| NFR-SCAL-003 | Qdrant filters always include org (+ source) |
| NFR-SCAL-004 | DB/Redis connection pooling |
| NFR-SCAL-005 | Design for 1k workspaces, 10k docs/workspace without schema rewrite |
| NFR-SCAL-006 | Connector sync jobs isolated per integration |

---

## 3.4 Reliability (REL)

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-REL-001 | Availability (prod v1) | 99.5% monthly |
| NFR-REL-002 | Idempotent ingestion/reindex | Required |
| NFR-REL-003 | Transient retry with exponential backoff | ≥ 3 attempts |
| NFR-REL-004 | Migrations only via Alembic | Required |
| NFR-REL-005 | Soft-delete for critical entities | Required |
| NFR-REL-006 | LLM outage does not corrupt data | Required |

---

## 3.5 Security (SEC)

| ID | Requirement |
|----|-------------|
| NFR-SEC-001 | TLS in production |
| NFR-SEC-002 | Argon2id (preferred) or bcrypt password hashing |
| NFR-SEC-003 | Short-lived access JWT; rotating refresh tokens hashed at rest |
| NFR-SEC-004 | Server-side RBAC + department checks |
| NFR-SEC-005 | Mandatory tenant filters; IDOR tests |
| NFR-SEC-006 | Pydantic/Zod boundary validation |
| NFR-SEC-007 | Upload allow-list + size limits + malware scan port |
| NFR-SEC-008 | Rate limiting (auth, chat, upload) |
| NFR-SEC-009 | Security headers via Nginx |
| NFR-SEC-010 | Secrets via environment only |
| NFR-SEC-011 | Audit trail for privileged actions |
| NFR-SEC-012 | CORS allow-list |
| NFR-SEC-013 | CSRF protection when using cookie sessions |
| NFR-SEC-014 | Dependency scanning in CI (Phase 10) |

---

## 3.6 Privacy (PRIV)

| ID | Requirement |
|----|-------------|
| NFR-PRIV-001 | Tenant isolation by design |
| NFR-PRIV-002 | User/workspace data deletion workflows |
| NFR-PRIV-003 | Minimal PII (name, email, avatar) |
| NFR-PRIV-004 | Configurable retention for messages/docs |
| NFR-PRIV-005 | Document provider training opt-out guidance in ops docs |

---

## 3.7 Maintainability (MAIN)

| ID | Requirement |
|----|-------------|
| NFR-MAIN-001 | Clean Architecture layers; domain free of frameworks |
| NFR-MAIN-002 | SOLID ports/adapters for LLM, storage, vector, connectors |
| NFR-MAIN-003 | Repository/service patterns for domain persistence |
| NFR-MAIN-004 | TypeScript strict; Python type hints on public APIs |
| NFR-MAIN-005 | Reusable shadcn UI primitives |
| NFR-MAIN-006 | Unit + integration tests for auth, tenancy, RAG orchestration |
| NFR-MAIN-007 | OpenAPI as API contract source |
| NFR-MAIN-008 | ADR for major decisions |

---

## 3.8 Usability (UX)

| ID | Requirement |
|----|-------------|
| NFR-UX-001 | Desktop-first enterprise UI; usable tablet |
| NFR-UX-002 | Loading / empty / error states for core flows |
| NFR-UX-003 | Accessible interactive components (WCAG 2.1 AA progressive) |
| NFR-UX-004 | Clear citation panel and confidence display |
| NFR-UX-005 | Light/dark theme tokens |
| NFR-UX-006 | Motion via Framer Motion used sparingly for polish, not noise |

---

## 3.9 Observability (OBS)

| ID | Requirement |
|----|-------------|
| NFR-OBS-001 | Structured JSON logs in production |
| NFR-OBS-002 | `request_id` / `job_id` correlation |
| NFR-OBS-003 | Usage metrics: tokens, messages, storage |
| NFR-OBS-004 | Queue depth and failure rates visible to operators |
| NFR-OBS-005 | Admin audit query API |

---

## 3.10 Deployability (DEP)

| ID | Requirement |
|----|-------------|
| NFR-DEP-001 | Full stack via Docker Compose |
| NFR-DEP-002 | Env parity across local/staging/prod |
| NFR-DEP-003 | One-command developer bootstrap (scripted) |
| NFR-DEP-004 | Nginx reverse proxy configs |
| NFR-DEP-005 | GitHub Actions CI/CD pipelines (Phase 10 complete) |

---

## 3.11 Capacity Planning (Indicative)

| Resource | Planning Baseline |
|----------|-------------------|
| Workspaces | 1,000 |
| Users / workspace | 500 |
| Documents / workspace | 10,000 |
| Concurrent chats | 100 |
| Indexed repos / workspace | 50 (later) |

---

**Next:** [04-USER-STORIES.md](./04-USER-STORIES.md)
