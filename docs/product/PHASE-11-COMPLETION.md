# Phase 11 Completion Report

| Field | Value |
|-------|--------|
| Phase | 11 — Production Hardening Plus |
| Status | Complete |
| Version | 1.1.0 |

> Original roadmap ended at Phase 10. Phase 11 is a post-roadmap hardening slice.

## Delivered

### Integration testing
- `tests/conftest.py` with Postgres session rebind for sync ingestion  
- `tests/integration/test_tenant_flow.py` — multi-tenant isolation + register/org/kb/upload/chat/analytics  
- CI job `api-integration` with Postgres 16 service  

### Security automation
- `.github/dependabot.yml` (pip, npm, GitHub Actions)  
- CI `security` job: `pip-audit` + `npm audit` (non-blocking baseline)  

### Observability
- In-process HTTP metrics counters  
- `GET /metrics/prometheus` Prometheus text exposition  
- Queue gauges when DB available  

### API protection
- `RateLimitMiddleware` for `/api` and `/api/v1/auth/*` (configurable per-minute limits)  

### TLS
- `infra/nginx/conf.d/tls.example.conf` — HTTPS redirect, HSTS, restricted metrics  

## Run integration tests locally

```bash
# Postgres must be reachable
set TEST_DATABASE_URL=postgresql+psycopg://eaw:eaw_secret@localhost:5432/eaw_test
set DATABASE_URL=%TEST_DATABASE_URL%
cd apps/api
pytest tests/integration -m integration -q
```

## Next (optional Phase 12+)

- Fail CI on high CVE severity  
- OpenTelemetry traces  
- HttpOnly cookie refresh sessions  
- Managed secrets (AWS SM / Vault)  
