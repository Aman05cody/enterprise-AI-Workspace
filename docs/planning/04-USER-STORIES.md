# 4. User Stories

| Field | Value |
|-------|--------|
| Document ID | EAW-US-001 |
| Version | 1.0.0 |

---

## 4.1 Epic Map

| Epic | Name | Primary Phases |
|------|------|----------------|
| E1 | Identity & Access | 2 |
| E2 | Workspace, Departments & RBAC | 2 |
| E3 | Document Knowledge | 3–4 |
| E4 | Grounded AI Chat | 5 |
| E5 | GitHub Intelligence | 6 |
| E6 | Notion + Drive | 7 |
| E7 | Slack + Jira | 8 |
| E8 | Analytics & Admin | 9 |
| E9 | Hardening & Ship | 10 |

---

## 4.2 E1 — Identity & Access

| ID | Story | Priority |
|----|-------|----------|
| US-AUTH-01 | As a new user, I want to register with email/password so I can join the platform. | P0 |
| US-AUTH-02 | As a user, I want email verification so my identity is trusted. | P0 |
| US-AUTH-03 | As a user, I want to log in and receive secure tokens. | P0 |
| US-AUTH-04 | As a user, I want Google OAuth so onboarding is frictionless. | P0 |
| US-AUTH-05 | As a user, I want GitHub OAuth so engineering teams can use existing identity. | P0 |
| US-AUTH-06 | As a user, I want password reset so I can recover access. | P0 |
| US-AUTH-07 | As a user, I want logout that revokes refresh tokens. | P0 |
| US-AUTH-08 | As the app, I want token refresh so sessions stay secure and continuous. | P0 |

**Acceptance (US-AUTH-03):** access ≤15m lifetime configurable; refresh stored hashed; invalid creds generic error.

---

## 4.3 E2 — Workspace, Departments & RBAC

| ID | Story | Priority |
|----|-------|----------|
| US-ORG-01 | As a user, I want to create a workspace so my company has an isolated tenant. | P0 |
| US-ORG-02 | As an admin, I want to invite members by email and role. | P0 |
| US-ORG-03 | As an invitee, I want to accept an invite and join. | P0 |
| US-ORG-04 | As an admin, I want to manage roles (Owner/Admin/Manager/Employee/Guest). | P0 |
| US-ORG-05 | As an admin, I want departments so access can be scoped. | P0 |
| US-ORG-06 | As a multi-workspace user, I want to switch active workspace. | P1 |
| US-ORG-07 | As an owner, I want workspace settings (AI defaults, limits). | P0 |
| US-ORG-08 | As an admin, I want billing-ready plan/seat fields even before payments. | P0 |

---

## 4.4 E3 — Document Knowledge

| ID | Story | Priority |
|----|-------|----------|
| US-DOC-01 | As an employee, I want to upload PDF/DOCX/TXT/MD/CSV/PPTX into a knowledge base. | P0 |
| US-DOC-02 | As a user, I want processing status so I know when content is ready. | P0 |
| US-DOC-03 | As a user, I want document metadata and preview. | P1 |
| US-DOC-04 | As a user, I want to search documents I am allowed to see. | P1 |
| US-DOC-05 | As an admin, I want versioning so updates replace stale knowledge. | P0 |
| US-DOC-06 | As a user, I want clear failure reasons when ingestion fails. | P0 |
| US-DOC-07 | As an admin, I want reprocess to rebuild the index. | P1 |
| US-DOC-08 | As the system, I want OCR on scanned PDFs so image-only docs are usable. | P1 |
| US-DOC-09 | As a user, I want AI tags/summaries on documents. | P1 |

---

## 4.5 E4 — Grounded AI Chat

| ID | Story | Priority |
|----|-------|----------|
| US-CHAT-01 | As an employee, I want to chat against workspace knowledge with streaming answers. | P0 |
| US-CHAT-02 | As a user, I want citations for every grounded claim. | P0 |
| US-CHAT-03 | As a user, I want a confidence score so I can judge reliability. | P0 |
| US-CHAT-04 | As a user, I want the AI to refuse when context is insufficient. | P0 |
| US-CHAT-05 | As a user, I want conversation history. | P0 |
| US-CHAT-06 | As a user, I want memory of prior turns without blowing the context window. | P1 |
| US-CHAT-07 | As a user, I want suggested follow-up questions. | P1 |
| US-CHAT-08 | As a user, I want to rate answers. | P1 |

**Acceptance (US-CHAT-02/04):** no citations when refusing; never invent source titles; org+permission filters enforced.

---

## 4.6 E5 — GitHub Intelligence

| ID | Story | Priority |
|----|-------|----------|
| US-GH-01 | As a developer, I want to connect GitHub and index repos. | P2 (Ph6) |
| US-GH-02 | As a developer, I want to chat with a repository. | P2 |
| US-GH-03 | As a developer, I want architecture explanations and docs generation. | P2 |
| US-GH-04 | As a reviewer, I want PR review assistance. | P2 |
| US-GH-05 | As a developer, I want test generation and function explanations. | P2 |

---

## 4.7 E6 — Notion + Drive

| ID | Story | Priority |
|----|-------|----------|
| US-NOTION-01 | As a PM, I want Notion pages synced into knowledge. | P2 |
| US-DRIVE-01 | As an employee, I want Drive folders auto-indexed. | P2 |

---

## 4.8 E7 — Slack + Jira

| ID | Story | Priority |
|----|-------|----------|
| US-SLACK-01 | As a manager, I want channel summaries and AI search. | P2 |
| US-JIRA-01 | As a manager, I want sprint summaries and story explanations. | P2 |

---

## 4.9 E8 — Analytics & Admin

| ID | Story | Priority |
|----|-------|----------|
| US-ANL-01 | As an admin, I want active users and AI usage charts. | P1 |
| US-ANL-02 | As an admin, I want popular documents and search trends. | P1 |
| US-ANL-03 | As an admin, I want department activity and storage usage. | P1 |
| US-AUD-01 | As an admin, I want audit logs for security investigations. | P0 |

---

## 4.10 E9 — Platform

| ID | Story | Priority |
|----|-------|----------|
| US-OPS-01 | As an operator, I want health/ready probes. | P0 |
| US-OPS-02 | As a developer, I want Docker Compose for full local stack. | P0 |
| US-OPS-03 | As a team, I want CI/CD and deployment docs. | P1 |

---

## 4.11 Personas

| Persona | Needs |
|---------|-------|
| Knowledge Worker | Fast, cited answers; simple upload |
| Engineering Lead | Repo chat, PR help, architecture insight |
| Workspace Admin | Control, audit, analytics, safe invites |
| Security Reviewer | Isolation, logs, rate limits, validation |
| Operator | Health, deploys, observability |

---

**Next:** [../architecture/05-SYSTEM-ARCHITECTURE.md](../architecture/05-SYSTEM-ARCHITECTURE.md)
