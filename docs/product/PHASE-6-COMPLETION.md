# Phase 6 Completion Report

| Field | Value |
|-------|--------|
| Phase | 6 — GitHub Intelligence |
| Status | Complete |
| Version | 0.6.0 |

## Delivered

### Connector core
- Tables: `connectors`, `connector_resources`, `connector_sync_jobs`
- Migration `20260711_0005_phase6_github`
- Secrets encrypted at rest (Fernet derived from `JWT_SECRET`)
- Connect via **GitHub PAT** (repo scope); disconnect clears credentials

### Repo workflow
1. Connect PAT → verify with `/user`  
2. Refresh repo catalog  
3. Select repos to sync  
4. Sync → create KB `GitHub · owner/repo` → fetch indexable files → `ingest_text` → RAG pipeline  

### Intelligence APIs (`/api/v1/github/...`)
| Endpoint | Capability |
|----------|------------|
| `POST /connect` | Connect PAT |
| `GET /connectors` | List |
| `DELETE /connectors/{id}` | Disconnect |
| `POST .../refresh-repos` | Refresh catalog |
| `GET .../repos` | List resources |
| `PUT .../repos/selection` | Enable repos |
| `POST .../sync` | Index selected repos |
| `POST /pulls/review` | PR review from diff |
| `POST /explain` | Explain file |
| `POST /generate-docs` | Generate documentation |
| `POST /generate-tests` | Generate tests |
| `POST /repos/{id}/architecture` | Architecture via RAG chat |
| `POST /repos/{id}/chat` | Chat with indexed repo |

### Frontend
- `/connectors/github` full management + tools UI  
- Dashboard link  

### Celery
- Task `eaw.github_sync` with sync fallback  

## Security notes
- Tokens never returned in API responses  
- Admin+ required for connect/sync/selection  
- Org membership required for intelligence tools  

## Next
Phase 7 — Notion + Google Drive  

Stop until **NEXT PHASE**.
