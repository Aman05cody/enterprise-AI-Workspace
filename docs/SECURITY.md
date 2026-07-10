# Security Checklist — Enterprise AI Workspace

| Field | Value |
|-------|--------|
| Document ID | EAW-SEC-001 |
| Version | 1.0.0 |
| Phase | 10 |

---

## Authentication & sessions

- [x] Passwords hashed (bcrypt)  
- [x] Short-lived JWT access tokens  
- [x] Refresh tokens stored hashed; rotation on refresh  
- [x] Logout revokes refresh tokens  
- [ ] Prefer HttpOnly cookies for refresh in browser production hardening  
- [x] OAuth providers scaffolded (enable with client secrets)  

## Multi-tenancy

- [x] `organization_id` on tenant resources  
- [x] Membership checks on protected services  
- [x] Vector payload filters require org + KB  
- [ ] Continuous automated tenant isolation suite (expand in CI with Postgres service)  

## Authorization

- [x] RBAC: owner / admin / manager / employee / guest  
- [x] Last-owner protection  
- [x] Analytics Manager+, audit Admin+  

## Data protection

- [x] Secrets via environment  
- [x] Connector tokens encrypted at rest (Fernet)  
- [x] Upload allow-list + size limits + magic bytes  
- [x] Soft-delete for critical entities  
- [ ] Production virus scanning adapter wired  

## Edge / transport

- [x] Nginx security headers template  
- [x] Rate limit zones for API/auth  
- [x] CORS allow-list config  
- [ ] TLS certificates in production  
- [ ] Restrict `/metrics` exposure  

## Application hardening

- [x] Pydantic/Zod boundary validation  
- [x] Structured error envelope (no stack traces to clients)  
- [x] Request ID middleware  
- [x] Non-root containers (prod Dockerfiles)  
- [x] Healthchecks on containers  

## Operations

- [x] Audit log writes for auth, org, connectors, docs  
- [x] Usage events for cost visibility  
- [ ] Secret rotation runbook  
- [x] Dependabot config (pip, npm, actions)  
- [x] pip-audit + npm audit jobs in CI (baseline non-blocking)  
- [x] API rate limiting middleware (auth + general API)  
- [x] Prometheus metrics endpoint (`/metrics/prometheus`)  
- [x] TLS Nginx example with HSTS + metrics IP restriction  


## AI / RAG safety

- [x] Grounded prompts + refuse path  
- [x] Citations when context present  
- [x] Configurable `RAG_MIN_SCORE`  
- [ ] Offline evaluation harness in CI (future)  

---

## Production must-dos before go-live

1. Replace all default secrets (`JWT_SECRET`, DB password, MinIO keys).  
2. Enable HTTPS and lock CORS to real origins.  
3. Disable `APP_DEBUG`.  
4. Restrict OpenAPI/docs if not public.  
5. Backups + restore drill.  
6. Set provider API key budgets / rate limits.  
