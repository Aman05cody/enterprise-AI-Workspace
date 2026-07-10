# Enterprise AI Workspace — Interview Questions

Use this guide for **project walkthroughs**, **system design**, and **deep dives** on this codebase.  
Answers should reference real modules under `apps/api` and `apps/web` when possible.

---

## 1. Project overview (warm-up)

1. What problem does Enterprise AI Workspace solve that a simple ChatGPT wrapper does not?
2. Who are the primary users (roles), and what can each role do?
3. Walk through the high-level architecture in 2 minutes (web, API, DB, vectors, workers).
4. What does “multi-tenant” mean in this product? How is isolation enforced?
5. What is the difference between a **workspace (organization)**, a **knowledge base**, and a **document**?
6. Why did you choose a monorepo (`apps/api` + `apps/web`) instead of separate repos?
7. What is production-ready about this project vs. what is still demo/dev mode?

**Expected talking points:** grounded RAG + citations, RBAC, connectors, analytics, Docker/CI, deploy path.

---

## 2. Authentication & security

8. How does JWT auth work here (access vs refresh tokens)?
9. What is refresh token rotation and why does it matter?
10. How would you store tokens safely in a SPA (localStorage vs httpOnly cookies)? Trade-offs?
11. How is password hashing done? Why bcrypt (or similar) over plain hashing?
12. Explain RBAC roles: Owner, Admin, Manager, Employee, Guest — give one example permission each.
13. How does the API know which organization a request belongs to?
14. What is the `X-Organization-Id` header used for?
15. How would you prevent IDOR (accessing another tenant’s knowledge base by guessing UUIDs)?
16. What rate limiting exists and where does it sit in the request pipeline?
17. How would you handle secret management in production (`JWT_SECRET`, DB URL, OpenAI keys)?
18. What CORS settings are required when frontend and API are on different Render domains?
19. How would you add OAuth (Google/GitHub) without breaking existing email/password login?
20. What would you log for audit vs. what must you never log (PII/secrets)?

---

## 3. Multi-tenancy & data model

21. Sketch the core tables: users, organizations, memberships, knowledge bases, documents, chunks, conversations.
22. How do foreign keys + `organization_id` enforce tenant boundaries?
23. Soft delete vs hard delete for documents — when would you use each?
24. How would departments fit into access control?
25. How do you design unique constraints for org-scoped slugs/names?
26. What indexes would you add for “list documents in KB sorted by updated_at”?
27. How would you migrate schema safely in production (Alembic)?
28. What happens if two users upload the same file name to the same knowledge base?

---

## 4. Document ingestion & storage

29. End-to-end flow when a user uploads a PDF.
30. Sync vs async ingestion (`INGESTION_MODE`) — when is each appropriate?
31. What file types are supported and how is validation done?
32. Local storage vs S3/MinIO — trade-offs for this product.
33. How do you prevent malware/oversized uploads?
34. How is text extracted from PDF / DOCX / PPTX / TXT?
35. What is chunking? Why chunk size and overlap matter?
36. What metadata do you store per chunk for citations later?
37. How do you reprocess a failed document?
38. How would you make uploads durable on ephemeral hosts (e.g. free Render disk)?

---

## 5. Embeddings, vectors & retrieval (RAG core)

39. What is an embedding? Why not keyword search alone?
40. What does `EMBEDDING_PROVIDER=hash` mean vs OpenAI embeddings? When is hash useful?
41. Why is `VECTOR_STORE_BACKEND=memory` bad for multi-instance production?
42. How does Qdrant fit into the architecture?
43. Explain hybrid retrieval (if implemented): dense + sparse/keyword.
44. What is top-k retrieval? How do you choose k?
45. What is reranking and why do you rerank after retrieval?
46. How do you decide the answer is not grounded enough to refuse?
47. How are **citations** constructed for the UI?
48. How do you avoid prompt injection from document content?
49. How would you evaluate RAG quality (offline metrics + human eval)?
50. How would you version embeddings when you change models?

---

## 6. Chat / LLM layer

51. Streaming responses with SSE — how does the client consume tokens?
52. What is the difference between `LLM_PROVIDER=echo` and a real model?
53. How is conversation history truncated or summarized for context limits?
54. System prompt design for grounded enterprise chat — what rules belong there?
55. Temperature settings for factual enterprise Q&A vs creative tasks?
56. How do you measure latency (TTFT vs total)?
57. How would you implement “regenerate answer” safely?
58. How would you add tool calling (search KB, search Jira) without breaking citations?

---

## 7. Connectors (GitHub, Notion, Drive, Slack, Jira)

59. What is a connector in this system? Shared pattern vs per-provider code?
60. How do you store third-party tokens securely?
61. GitHub: what do you index, and what do you skip (binaries, huge files)?
62. How would you design incremental sync vs full reindex?
63. Rate limits from external APIs — how do you handle retries/backoff?
64. Webhooks vs polling for GitHub/Slack — pros/cons?
65. How do connector-sourced docs appear in the same RAG pipeline as uploads?
66. Security: least privilege OAuth scopes — give examples per connector.
67. How would you isolate connector failures so one provider does not take down chat?

---

## 8. Backend engineering (FastAPI / Python)

68. Why FastAPI for this API? Alternatives?
69. How are dependencies injected (`get_db`, current user)?
70. How are API errors standardized (error envelope)?
71. Where would you put business logic: routers vs services vs domain?
72. Celery worker role — which tasks are background?
73. How does Redis relate to Celery (and what if Redis is down)?
74. SQLAlchemy sessions: request-scoped lifecycle and common pitfalls.
75. How would you add pagination consistently across list endpoints?
76. How do you write unit tests that don’t need a real Postgres?
77. What integration tests would you run in CI with a Postgres service?
78. How would you structure feature flags for “connectors beta”?

---

## 9. Frontend (Next.js / React)

79. App Router layout: public landing vs auth vs authenticated shell.
80. Why is `NEXT_PUBLIC_API_URL` a build-time concern on Render?
81. How does the dashboard keep auth state (tokens) and redirect unauthenticated users?
82. How would you improve UX for long-running ingestion (polling vs websockets)?
83. How is the chat UI structured (conversations list, messages, citations panel)?
84. Accessibility basics for forms (labels, errors, focus).
85. How would you add a light/dark theme without breaking design tokens?
86. Performance: what would you code-split or lazy-load first?
87. How would you handle API errors globally (toasts, retry, sign-out on 401)?
88. Testing strategy for critical flows (register → create KB → upload → chat).

---

## 10. DevOps, Docker, CI/CD, Render

89. What does `docker-compose.yml` run locally vs `docker-compose.prod.yml`?
90. Multi-stage Docker builds — why for API and Next.js?
91. What does the GitHub Actions CI pipeline check?
92. How does Alembic run on deploy (`start.sh`)?
93. Why normalize `DATABASE_URL` from `postgres://` to `postgresql+psycopg://`?
94. Free-tier Render sleep — impact on UX and how you’d explain it to stakeholders.
95. Blueprint (`render.yaml`) vs manual service creation — benefits?
96. Health checks: what should `/health` return and why?
97. How would you add Prometheus metrics and what would you alert on?
98. Zero-downtime deploy strategy for API + migrations.
99. How would you store uploads in production (S3) when containers are ephemeral?
100. Disaster recovery: what do you back up (DB, vectors, objects)?

---

## 11. System design (whiteboard)

101. Design a multi-tenant RAG SaaS for 10k companies. Where do you shard?
102. Design citation-backed chat with <2s p95 retrieval. Bottlenecks?
103. Design document permissioning: private / department / org-wide.
104. Design a job system for ingestion with retries, DLQ, and observability.
105. Design cost controls (token budgets per org/plan tier).
106. Design abuse prevention (spam uploads, prompt spam, scraping).
107. Design SSO (SAML/OIDC) for enterprise customers.
108. Design multi-region active-passive failover.
109. Design “bring your own model” (customer OpenAI/Azure keys).
110. Design evaluation pipeline before promoting a new prompt/model.

---

## 12. Debugging & scenarios

111. Users report empty answers after upload — list your debugging steps.
112. Chat works locally but CORS fails on Render — how do you fix it?
113. Migrations fail on deploy — how do you recover safely?
114. Vector search returns irrelevant chunks — what knobs do you turn?
115. API is slow only under load — how do you profile?
116. One tenant’s data appeared in another tenant’s answer — incident response?
117. Next.js build succeeded but API calls go to `localhost` in production — root cause?
118. Free Postgres plan unavailable on Render — alternatives and cutover steps?
119. Memory vector store “forgets” documents after restart — expected? How to fix?
120. Worker backlog grows forever — how do you detect and scale?

---

## 13. Behavioral / ownership

121. What was the hardest technical decision in this project and why?
122. What would you rewrite if you had two more weeks?
123. How did you phase delivery (planning → foundation → RAG → connectors → hardening)?
124. How do you balance “ship demo” vs “production quality”?
125. Describe a bug you fixed that only appeared in async/streaming paths.
126. How would you onboard a new engineer to this repo in one day?
127. How do you document architecture so future you doesn’t get lost?
128. Security review: top 5 risks you’d present to a CISO.

---

## 14. Quick code-reading challenges

Open the repo and answer:

129. Trace register → JWT issued → dashboard load (files involved).
130. Trace upload → extract → chunk → embed → vector upsert.
131. Trace chat message → retrieve → prompt → stream → citations JSON.
132. Find where organization membership is checked before KB access.
133. Find rate limit middleware and explain the algorithm.
134. Find how `echo` LLM formats a grounded-looking response.
135. Find Next.js `api` client interceptors for refresh tokens.
136. Find Render start command for API and why `workers=1` in demo mode.

---

## 15. Strong closing questions (you ask the interviewer)

- How does your team evaluate RAG quality in production?
- Do you prefer multi-tenant row-level isolation or schema-per-tenant?
- What’s your standard for citation UX with legal/compliance teams?
- How do you handle model/provider failover?

---

## Cheat sheet — map questions to this repo

| Topic | Look here |
|-------|-----------|
| Config / providers | `apps/api/src/eaw/core/config.py` |
| App entry / CORS | `apps/api/src/eaw/main.py` |
| Auth | `apps/api/src/eaw/application/services/auth_service.py`, `api/v1/auth.py` |
| RBAC | `apps/api/src/eaw/domain/tenancy/policies.py` |
| Documents | `application/services/document_service.py` |
| Ingestion | `application/services/ingestion_service.py`, `infrastructure/queue/tasks/` |
| RAG / chat | `chat_service.py`, `retrieval_service.py` |
| Vectors | `infrastructure/vector/` |
| Embeddings | `infrastructure/embeddings/` |
| Connectors | `application/services/*_service.py`, `infrastructure/connectors/` |
| Web shell | `apps/web/src/shared/ui/app-shell.tsx` |
| API client | `apps/web/src/shared/api/client.ts` |
| Deploy Render | `render.yaml`, `apps/api/start.sh`, `docs/RENDER.md` |
| Docker prod | `docker-compose.prod.yml`, `docs/DEPLOYMENT.md` |

---

## Suggested mock interview agenda (45 min)

| Time | Focus |
|------|--------|
| 0–5 | Project pitch + architecture diagram |
| 5–15 | Auth + multi-tenancy deep dive |
| 15–30 | RAG pipeline (upload → cite) |
| 30–40 | One connector + failure modes |
| 40–45 | Deploy/CI + “what next” |

---

*Generated for Enterprise AI Workspace interview prep. Keep answers honest: distinguish demo providers (hash/echo/memory) from production (OpenAI/Qdrant/S3/Postgres).*
