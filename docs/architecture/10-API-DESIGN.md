# 10. API Design

| Field | Value |
|-------|--------|
| Document ID | EAW-API-001 |
| Version | 1.0.0 |
| Base | `/api/v1` |
| Style | REST + SSE |
| Docs | OpenAPI / Swagger via FastAPI |

---

## 10.1 Conventions

### Headers
| Header | Purpose |
|--------|---------|
| `Authorization: Bearer <access>` | Auth |
| `X-Organization-Id` | Active workspace (validated) |
| `X-Request-Id` | Correlation |
| `Idempotency-Key` | Safe retries on creates/uploads |

### Envelope
```json
{
  "data": {},
  "meta": { "request_id": "...", "page": 1, "page_size": 20, "total": 0 }
}
```

```json
{
  "error": { "code": "INSUFFICIENT_CONTEXT", "message": "...", "details": {} },
  "meta": { "request_id": "..." }
}
```

### Status Codes
200, 201, 202, 204, 400, 401, 403, 404, 409, 422, 429, 500, 503

---

## 10.2 Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness |
| GET | `/ready` | No | Readiness (DB/Redis/Qdrant) |
| GET | `/api/v1/version` | No | Build info |

---

## 10.3 Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | No | Register |
| POST | `/api/v1/auth/login` | No | Login |
| POST | `/api/v1/auth/refresh` | Refresh | Rotate tokens |
| POST | `/api/v1/auth/logout` | Yes | Revoke refresh |
| GET | `/api/v1/auth/me` | Yes | Profile |
| PATCH | `/api/v1/auth/me` | Yes | Update profile |
| POST | `/api/v1/auth/verify-email` | No | Confirm email token |
| POST | `/api/v1/auth/resend-verification` | Yes/No | Resend |
| POST | `/api/v1/auth/password/forgot` | No | Reset request |
| POST | `/api/v1/auth/password/reset` | No | Reset confirm |
| GET | `/api/v1/auth/oauth/google/start` | No | Google OAuth start |
| GET | `/api/v1/auth/oauth/google/callback` | No | Google callback |
| GET | `/api/v1/auth/oauth/github/start` | No | GitHub OAuth start |
| GET | `/api/v1/auth/oauth/github/callback` | No | GitHub callback |

---

## 10.4 Workspaces & RBAC

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/organizations` | any user | Create workspace |
| GET | `/api/v1/organizations` | member | List my workspaces |
| GET | `/api/v1/organizations/{orgId}` | member | Get workspace |
| PATCH | `/api/v1/organizations/{orgId}` | admin+ | Update |
| GET | `/api/v1/organizations/{orgId}/settings` | admin+ | Settings |
| PATCH | `/api/v1/organizations/{orgId}/settings` | admin+ | Update settings |
| GET | `/api/v1/organizations/{orgId}/members` | member | List members |
| PATCH | `/api/v1/organizations/{orgId}/members/{userId}` | admin+ | Change role |
| DELETE | `/api/v1/organizations/{orgId}/members/{userId}` | admin+ | Remove |
| POST | `/api/v1/organizations/{orgId}/invites` | admin+ | Invite |
| GET | `/api/v1/organizations/{orgId}/invites` | admin+ | List invites |
| POST | `/api/v1/invites/{token}/accept` | auth | Accept invite |
| GET | `/api/v1/organizations/{orgId}/departments` | member | List depts |
| POST | `/api/v1/organizations/{orgId}/departments` | admin+ | Create dept |
| PATCH | `/api/v1/departments/{deptId}` | admin+ | Update |
| DELETE | `/api/v1/departments/{deptId}` | admin+ | Soft delete |
| PUT | `/api/v1/organizations/{orgId}/members/{userId}/departments` | admin+ | Assign depts |

---

## 10.5 Knowledge Bases & Documents

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/v1/knowledge-bases` | member | List |
| POST | `/api/v1/knowledge-bases` | manager+* | Create |
| GET | `/api/v1/knowledge-bases/{kbId}` | member | Detail |
| PATCH | `/api/v1/knowledge-bases/{kbId}` | manager+* | Update |
| DELETE | `/api/v1/knowledge-bases/{kbId}` | admin+ | Soft delete |
| GET | `/api/v1/knowledge-bases/{kbId}/stats` | member | Aggregates |
| GET | `/api/v1/knowledge-bases/{kbId}/documents` | member | List/filter |
| POST | `/api/v1/knowledge-bases/{kbId}/documents` | employee+ | Upload multipart |
| POST | `/api/v1/knowledge-bases/{kbId}/documents/batch` | employee+ | Batch (P1) |
| GET | `/api/v1/documents/{docId}` | member | Metadata |
| GET | `/api/v1/documents/{docId}/preview` | member | Preview/excerpt |
| GET | `/api/v1/documents/{docId}/versions` | member | Version list |
| POST | `/api/v1/documents/{docId}/versions` | employee+ | Upload new version |
| DELETE | `/api/v1/documents/{docId}` | policy | Soft delete |
| POST | `/api/v1/documents/{docId}/reprocess` | admin+ | Reindex |
| GET | `/api/v1/documents/{docId}/jobs` | member | Job history |
| GET | `/api/v1/documents/{docId}/download` | member | Download |
| POST | `/api/v1/knowledge-bases/{kbId}/search` | member | Hybrid doc search |

\*Department-scoped managers where policy enabled.

---

## 10.6 Chat

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/conversations` | List my conversations |
| POST | `/api/v1/conversations` | Create (body: kb_id/options) |
| GET | `/api/v1/conversations/{id}` | Get |
| PATCH | `/api/v1/conversations/{id}` | Rename |
| DELETE | `/api/v1/conversations/{id}` | Soft delete |
| GET | `/api/v1/conversations/{id}/messages` | History |
| POST | `/api/v1/conversations/{id}/messages` | Non-stream reply |
| POST | `/api/v1/conversations/{id}/messages:stream` | **SSE stream** |
| POST | `/api/v1/messages/{id}/feedback` | Rating |

### Stream events
`meta` · `token` · `citation` · `confidence` · `suggestions` · `usage` · `error` · `done`

### Message request
```json
{
  "content": "What is our remote work policy?",
  "options": {
    "top_k": 20,
    "rerank_top_n": 6,
    "temperature": 0.2,
    "include_suggestions": true
  }
}
```

### Assistant payload (final)
```json
{
  "content": "...",
  "confidence": 0.82,
  "citations": [
    {
      "document_id": "...",
      "chunk_id": "...",
      "title": "HR Policy.pdf",
      "excerpt": "...",
      "score": 0.91,
      "rank": 1
    }
  ],
  "suggestions": ["Who approves exceptions?", "What about contractors?"]
}
```

---

## 10.7 Connectors (Phased)

### Generic
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/connectors` | List |
| POST | `/api/v1/connectors/{type}/connect` | Start OAuth/connect |
| DELETE | `/api/v1/connectors/{id}` | Disconnect |
| GET | `/api/v1/connectors/{id}/resources` | List resources |
| PUT | `/api/v1/connectors/{id}/resources/selection` | Enable resources |
| POST | `/api/v1/connectors/{id}/sync` | Trigger sync |
| GET | `/api/v1/connectors/{id}/sync-jobs` | Sync history |

### GitHub-specific (Phase 6)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/github/repos/{repoId}/chat` | Repo-scoped chat |
| POST | `/api/v1/github/pulls/{pullId}/review` | PR review assist |
| POST | `/api/v1/github/explain` | Explain symbol/function |
| POST | `/api/v1/github/generate-docs` | Generate documentation |
| POST | `/api/v1/github/generate-tests` | Generate tests |

### Notion / Drive / Slack / Jira
Resource list + sync + specialized summary endpoints under `/api/v1/notion|drive|slack|jira/...`

---

## 10.8 Analytics & Audit

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/v1/analytics/overview` | admin+/manager* | KPIs |
| GET | `/api/v1/analytics/usage` | admin+ | Time series |
| GET | `/api/v1/analytics/search-trends` | admin+ | Trends |
| GET | `/api/v1/analytics/popular-documents` | admin+ | Top sources |
| GET | `/api/v1/analytics/departments` | admin+ | Dept activity |
| GET | `/api/v1/analytics/storage` | admin+ | Storage usage |
| GET | `/api/v1/audit-logs` | admin+ | Filterable audit |

---

## 10.9 Phase Mapping

| Phase | API Surface |
|-------|-------------|
| 2 | Health, auth, orgs, members, depts, RBAC |
| 3 | KB, documents, versions, preview, search |
| 4 | Jobs/progress (ingestion status) |
| 5 | Conversations, stream chat, citations |
| 6 | GitHub connector + intelligence APIs |
| 7 | Notion + Drive |
| 8 | Slack + Jira |
| 9 | Analytics full pack |
| 10 | Hardening only (no major new resources) |

---

**Next:** [11-FOLDER-STRUCTURE.md](./11-FOLDER-STRUCTURE.md)
