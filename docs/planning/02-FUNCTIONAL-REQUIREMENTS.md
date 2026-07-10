# 2. Functional Requirements

| Field | Value |
|-------|--------|
| Document ID | EAW-FR-001 |
| Version | 1.0.0 |
| Related | EAW-SRS-001 |

---

## 2.1 Conventions

| Priority | Meaning |
|----------|---------|
| **P0** | Must ship for core production path |
| **P1** | Should ship in first major release wave |
| **P2** | Planned enhancement / later module |

IDs: `FR-<DOMAIN>-<NNN>`

---

## 2.2 Authentication (AUTH)

| ID | Requirement | P |
|----|-------------|---|
| FR-AUTH-001 | Users shall register with email, full name, password. | P0 |
| FR-AUTH-002 | System shall verify email before full privileges (or soft-gate configurable). | P0 |
| FR-AUTH-003 | Users shall login with email/password and receive access + refresh tokens. | P0 |
| FR-AUTH-004 | System shall rotate refresh tokens and revoke on logout. | P0 |
| FR-AUTH-005 | System shall support Google OAuth signup/login. | P0 |
| FR-AUTH-006 | System shall support GitHub OAuth signup/login. | P0 |
| FR-AUTH-007 | System shall support password reset via secure time-limited token. | P0 |
| FR-AUTH-008 | System shall enforce password complexity policy. | P0 |
| FR-AUTH-009 | System shall link OAuth identity to existing account by verified email when policy allows. | P1 |
| FR-AUTH-010 | Auth errors shall avoid user-enumeration where practical. | P0 |

---

## 2.3 Organizations / Workspaces (ORG)

| ID | Requirement | P |
|----|-------------|---|
| FR-ORG-001 | Authenticated users shall create a workspace (organization). | P0 |
| FR-ORG-002 | Creator shall become `owner`. | P0 |
| FR-ORG-003 | Workspace shall have name, slug, logo, settings JSON. | P0 |
| FR-ORG-004 | All tenant resources shall be scoped by `organization_id`. | P0 |
| FR-ORG-005 | Users may belong to multiple workspaces and switch active workspace. | P1 |
| FR-ORG-006 | Workspace settings shall include AI defaults, limits, retention. | P0 |
| FR-ORG-007 | Data model shall be billing-ready (plan, seats, usage counters hooks). | P0 |
| FR-ORG-008 | Owner shall soft-delete workspace with cascade policies. | P2 |

---

## 2.4 Departments (DEPT)

| ID | Requirement | P |
|----|-------------|---|
| FR-DEPT-001 | Admins shall create departments within a workspace. | P0 |
| FR-DEPT-002 | Members may be assigned to one or more departments. | P0 |
| FR-DEPT-003 | Knowledge bases/documents may be restricted by department. | P1 |
| FR-DEPT-004 | Managers shall have elevated permissions within their departments. | P1 |

---

## 2.5 RBAC (RBAC)

Roles: **Owner · Admin · Manager · Employee · Guest**

| ID | Requirement | P |
|----|-------------|---|
| FR-RBAC-001 | System shall enforce the five roles server-side. | P0 |
| FR-RBAC-002 | Permission checks shall combine role + department scope. | P1 |
| FR-RBAC-003 | Admins/Owners shall invite users with role (+ optional department). | P0 |
| FR-RBAC-004 | Invitees shall accept invites and join workspace. | P0 |
| FR-RBAC-005 | Admins/Owners shall change roles (only Owner assigns Owner). | P0 |
| FR-RBAC-006 | Admins/Owners shall remove members. | P0 |
| FR-RBAC-007 | Last Owner cannot leave/demote self. | P0 |
| FR-RBAC-008 | Guests shall have read-limited chat/search by policy. | P0 |

### Permission Matrix (v1 Baseline)

| Capability | Owner | Admin | Manager | Employee | Guest |
|------------|:-----:|:-----:|:-------:|:--------:|:-----:|
| Billing / destroy workspace | ✓ | | | | |
| Manage members & roles | ✓ | ✓ | | | |
| Manage departments | ✓ | ✓ | limited | | |
| Manage connectors | ✓ | ✓ | | | |
| Create/manage knowledge bases | ✓ | ✓ | ✓* | | |
| Upload documents | ✓ | ✓ | ✓ | ✓ | |
| Delete any document | ✓ | ✓ | ✓* | | |
| Delete own document | ✓ | ✓ | ✓ | ✓ | |
| Chat / search allowed sources | ✓ | ✓ | ✓ | ✓ | ✓* |
| View workspace analytics | ✓ | ✓ | ✓* | | |
| View audit logs | ✓ | ✓ | | | |

\*Department-scoped where applicable.

---

## 2.6 Knowledge Bases (KB)

| ID | Requirement | P |
|----|-------------|---|
| FR-KB-001 | Authorized users shall create knowledge bases (collections). | P0 |
| FR-KB-002 | KB shall support name, description, department scope, settings. | P0 |
| FR-KB-003 | Users shall list KBs visible to their role/department. | P0 |
| FR-KB-004 | Admins shall update/archive/soft-delete KBs. | P0 |
| FR-KB-005 | KB shall expose document counts and processing aggregates. | P0 |

---

## 2.7 Documents (DOC)

| ID | Requirement | P |
|----|-------------|---|
| FR-DOC-001 | Upload supported types: PDF, DOCX, TXT, MD, CSV, PPTX. | P0 |
| FR-DOC-002 | Enforce MIME allow-list, extension check, max size. | P0 |
| FR-DOC-003 | Store files in S3-compatible storage via abstraction. | P0 |
| FR-DOC-004 | Track status: `pending`, `processing`, `ready`, `failed`, `deleted`. | P0 |
| FR-DOC-005 | Extract metadata (size, pages, checksum, language if available). | P0 |
| FR-DOC-006 | Support document versioning (new version supersedes prior for retrieval). | P0 |
| FR-DOC-007 | Preview metadata and text excerpt when available. | P1 |
| FR-DOC-008 | Full-text / hybrid document search within workspace permissions. | P1 |
| FR-DOC-009 | Soft-delete + vector cleanup. | P0 |
| FR-DOC-010 | Reprocess/reindex document. | P1 |
| FR-DOC-011 | Batch upload. | P1 |
| FR-DOC-012 | Virus scan hook (placeholder interface). | P1 |
| FR-DOC-013 | OCR for scanned PDFs/images. | P1 |
| FR-DOC-014 | AI document tagging (auto labels). | P1 |
| FR-DOC-015 | AI document summary generation. | P1 |

---

## 2.8 Ingestion Pipeline (ING)

| ID | Requirement | P |
|----|-------------|---|
| FR-ING-001 | Upload enqueues Celery ingestion job. | P0 |
| FR-ING-002 | Pipeline: extract → clean → chunk → embed → upsert Qdrant. | P0 |
| FR-ING-003 | Configurable chunk size/overlap per KB/workspace. | P0 |
| FR-ING-004 | Idempotent reprocess replaces prior chunks/vectors. | P0 |
| FR-ING-005 | Retry transient failures with backoff. | P0 |
| FR-ING-006 | Persist job progress and failure reasons. | P0 |
| FR-ING-007 | Record embedding model version on chunks/docs. | P0 |
| FR-ING-008 | OCR stage when text extraction yields insufficient text. | P1 |

---

## 2.9 Retrieval & Generation (RAG)

| ID | Requirement | P |
|----|-------------|---|
| FR-RAG-001 | Hybrid retrieval (dense + sparse/keyword + metadata filters). | P0 |
| FR-RAG-002 | Cross-encoder re-ranking of candidates. | P0 |
| FR-RAG-003 | Context compression before LLM prompt assembly. | P0 |
| FR-RAG-004 | LLM generation with grounding instructions. | P0 |
| FR-RAG-005 | Citations required on grounded answers. | P0 |
| FR-RAG-006 | Confidence score exposed to client. | P0 |
| FR-RAG-007 | Refuse/insufficient-context path when retrieval weak. | P0 |
| FR-RAG-008 | Provider abstraction for chat + embeddings (OpenAI default; Grok/Gemini/OpenRouter swappable). | P0 |
| FR-RAG-009 | Token usage logged per request. | P0 |

---

## 2.10 Enterprise Chat (CHAT)

| ID | Requirement | P |
|----|-------------|---|
| FR-CHAT-001 | Create conversations scoped to workspace (+ optional KB set). | P0 |
| FR-CHAT-002 | Send messages; receive streaming answers (SSE). | P0 |
| FR-CHAT-003 | Persist conversation history. | P0 |
| FR-CHAT-004 | Conversation memory (summarized long-term memory within conversation/workspace policy). | P1 |
| FR-CHAT-005 | Suggested follow-up questions. | P1 |
| FR-CHAT-006 | Rename/delete conversations. | P0 |
| FR-CHAT-007 | Message feedback (up/down). | P1 |
| FR-CHAT-008 | Rate limits per user/workspace. | P0 |

---

## 2.11 GitHub Module (GH) — Phase 6

| ID | Requirement | P |
|----|-------------|---|
| FR-GH-001 | Connect GitHub account/org via OAuth/App. | P2* |
| FR-GH-002 | Select and index repositories. | P2* |
| FR-GH-003 | Chat with repository knowledge. | P2* |
| FR-GH-004 | Explain architecture / generate documentation. | P2* |
| FR-GH-005 | Review pull requests (summary + risks). | P2* |
| FR-GH-006 | Generate tests / explain functions. | P2* |

\*P0 within Phase 6 module delivery.

---

## 2.12 Notion Module (NOTION) — Phase 7

| ID | Requirement | P |
|----|-------------|---|
| FR-NOTION-001 | Import pages / sync workspace. | P2 |
| FR-NOTION-002 | Index content into vector store with source metadata. | P2 |
| FR-NOTION-003 | Search and cite Notion sources in chat. | P2 |

---

## 2.13 Google Drive Module (DRIVE) — Phase 7

| ID | Requirement | P |
|----|-------------|---|
| FR-DRIVE-001 | Connect Drive; select folders. | P2 |
| FR-DRIVE-002 | Automatic / scheduled indexing. | P2 |
| FR-DRIVE-003 | Change detection and reindex. | P2 |

---

## 2.14 Slack Module (SLACK) — Phase 8

| ID | Requirement | P |
|----|-------------|---|
| FR-SLACK-001 | Connect workspace; select channels. | P2 |
| FR-SLACK-002 | Channel summaries. | P2 |
| FR-SLACK-003 | AI search over indexed messages. | P2 |
| FR-SLACK-004 | Meeting recap generation (from threads/channels). | P2 |

---

## 2.15 Jira Module (JIRA) — Phase 8

| ID | Requirement | P |
|----|-------------|---|
| FR-JIRA-001 | Connect Jira site. | P2 |
| FR-JIRA-002 | Issue search via AI and filters. | P2 |
| FR-JIRA-003 | Sprint summaries. | P2 |
| FR-JIRA-004 | Story explanation grounded on issue fields/comments. | P2 |

---

## 2.16 Future Connectors (FUT)

| ID | Requirement | P |
|----|-------------|---|
| FR-FUT-001 | OneDrive, SharePoint, Email connectors. | P2 |
| FR-FUT-002 | Voice queries. | P2 |

---

## 2.17 Analytics (ANL)

| ID | Requirement | P |
|----|-------------|---|
| FR-ANL-001 | Active users metrics. | P1 |
| FR-ANL-002 | AI usage (messages, tokens, cost proxies). | P1 |
| FR-ANL-003 | Search trends. | P1 |
| FR-ANL-004 | Popular documents / most cited sources. | P1 |
| FR-ANL-005 | Department activity. | P1 |
| FR-ANL-006 | Storage usage. | P1 |

---

## 2.18 Security & Audit (SEC)

| ID | Requirement | P |
|----|-------------|---|
| FR-SEC-001 | HTTPS-ready deployment (TLS at Nginx). | P0 |
| FR-SEC-002 | Rate limiting on auth and AI endpoints. | P0 |
| FR-SEC-003 | Audit logs for auth, RBAC, deletes, connector, settings. | P0 |
| FR-SEC-004 | Secure headers (HSTS, CSP baseline, etc.). | P0 |
| FR-SEC-005 | ORM parameterization (SQLi protection). | P0 |
| FR-SEC-006 | Output encoding / React defaults (XSS protection). | P0 |
| FR-SEC-007 | CSRF strategy for cookie-based flows. | P0 |
| FR-SEC-008 | File validation pipeline. | P0 |
| FR-SEC-009 | Virus scan placeholder port. | P1 |

---

## 2.19 Platform Ops (OPS)

| ID | Requirement | P |
|----|-------------|---|
| FR-OPS-001 | `/health` and `/ready` endpoints. | P0 |
| FR-OPS-002 | Structured logs with request/job correlation IDs. | P0 |
| FR-OPS-003 | Docker Compose local/prod profiles. | P0 |
| FR-OPS-004 | GitHub Actions CI (lint/test/build). | P1 |
| FR-OPS-005 | OpenAPI/Swagger for API. | P0 |

---

**Next:** [03-NON-FUNCTIONAL-REQUIREMENTS.md](./03-NON-FUNCTIONAL-REQUIREMENTS.md)
