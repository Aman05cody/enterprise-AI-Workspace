# Phase 7 Completion Report

| Field | Value |
|-------|--------|
| Phase | 7 — Notion + Google Drive |
| Status | Complete |
| Version | 0.7.0 |

## Delivered

### Shared connector foundation
- Reuses `connectors` / `connector_resources` / `connector_sync_jobs`
- `ConnectorServiceBase` for encrypt, RBAC, selection, KB helpers
- Celery tasks: `eaw.notion_sync`, `eaw.gdrive_sync` (+ sync fallback)

### Notion
- Connect with **internal integration token**
- Refresh/list pages shared with the integration
- Select pages → sync → KB **“Notion Workspace”**
- Blocks converted to Markdown-ish text → RAG ingest (`source_type=notion`)

### Google Drive
- Connect with **OAuth access token** (+ optional refresh)
- List root folders (+ root resource)
- Select folders → recursive file walk
- Export Google Docs/Sheets/Slides; download text-like files
- KB **“Google Drive”** (`source_type=gdrive`)

### API
| Area | Prefix |
|------|--------|
| Notion | `/api/v1/notion/*` |
| Drive | `/api/v1/drive/*` |

### UI
- `/connectors/notion`
- `/connectors/drive`
- Dashboard links

## Ops notes
1. Notion: share each page with the integration before refresh sees it.  
2. Drive: token needs `drive.readonly` (or broader) scope.  
3. Secrets encrypted at rest; never returned in API responses.

## Next
Phase 8 — Slack + Jira  

Stop until **NEXT PHASE**.
