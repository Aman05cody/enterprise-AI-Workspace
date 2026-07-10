# 11. Folder Structure

| Field | Value |
|-------|--------|
| Document ID | EAW-FS-001 |
| Version | 1.0.0 |
| Note | Target structure for implementation phases — **no code in Phase 1** |

---

## 11.1 Monorepo Root

```text
enterprise-ai-workspace/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── .editorconfig
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
│
├── docs/                          # Phase 1 deliverable (this tree)
│   ├── README.md
│   ├── planning/
│   ├── architecture/
│   ├── diagrams/
│   ├── product/
│   └── adr/
│
├── apps/
│   ├── api/                       # FastAPI
│   └── web/                       # Next.js 15
│
├── packages/                      # optional shared contracts later
│   └── openapi-types/
│
├── infra/
│   ├── docker/
│   │   ├── api.Dockerfile
│   │   ├── web.Dockerfile
│   │   └── worker.Dockerfile
│   ├── nginx/
│   │   └── conf.d/default.conf
│   └── github-actions/
│       ├── ci.yml
│       └── cd.yml
│
└── scripts/
    ├── bootstrap.sh
    ├── bootstrap.ps1
    └── seed/
```

---

## 11.2 Backend (`apps/api`)

```text
apps/api/
├── pyproject.toml
├── alembic.ini
├── Dockerfile
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── src/eaw/
    ├── main.py
    ├── worker.py
    ├── domain/
    │   ├── common/
    │   ├── identity/
    │   ├── tenancy/
    │   ├── knowledge/
    │   ├── conversation/
    │   ├── connectors/
    │   └── audit/
    ├── application/
    │   ├── ports/
    │   │   ├── repositories.py
    │   │   ├── llm.py
    │   │   ├── embeddings.py
    │   │   ├── vector_store.py
    │   │   ├── object_storage.py
    │   │   ├── ocr.py
    │   │   ├── virus_scan.py
    │   │   ├── email.py
    │   │   └── connector.py
    │   ├── services/
    │   │   ├── auth_service.py
    │   │   ├── org_service.py
    │   │   ├── document_service.py
    │   │   ├── ingestion_service.py
    │   │   ├── retrieval_service.py
    │   │   ├── chat_service.py
    │   │   ├── github_service.py
    │   │   └── analytics_service.py
    │   └── dto/
    ├── infrastructure/
    │   ├── db/
    │   │   ├── models/
    │   │   ├── repositories/
    │   │   └── migrations/
    │   ├── cache/
    │   ├── queue/
    │   │   └── tasks/
    │   ├── storage/
    │   ├── vector/
    │   ├── llm/
    │   ├── embeddings/
    │   ├── rerank/
    │   ├── rag/
    │   ├── ocr/
    │   ├── oauth/
    │   ├── connectors/
    │   │   ├── github/
    │   │   ├── notion/
    │   │   ├── gdrive/
    │   │   ├── slack/
    │   │   └── jira/
    │   └── email/
    ├── api/
    │   ├── v1/
    │   │   ├── auth.py
    │   │   ├── organizations.py
    │   │   ├── departments.py
    │   │   ├── knowledge_bases.py
    │   │   ├── documents.py
    │   │   ├── conversations.py
    │   │   ├── connectors.py
    │   │   ├── github.py
    │   │   ├── analytics.py
    │   │   └── audit.py
    │   ├── deps.py
    │   ├── middleware.py
    │   ├── errors.py
    │   └── schemas/
    └── core/
        ├── config.py
        ├── logging.py
        ├── security.py
        └── container.py
```

### Import rule
`domain` ← `application` ← `api` / `infrastructure`  
Domain never imports infrastructure or FastAPI.

---

## 11.3 Frontend (`apps/web`)

```text
apps/web/
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── components.json
├── public/
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── (auth)/
    │   │   ├── login/
    │   │   ├── register/
    │   │   └── reset-password/
    │   └── (app)/
    │       ├── layout.tsx
    │       ├── dashboard/
    │       ├── knowledge/
    │       ├── chat/
    │       ├── connectors/
    │       ├── analytics/
    │       └── settings/
    ├── features/
    │   ├── auth/
    │   ├── workspace/
    │   ├── knowledge/
    │   ├── chat/
    │   ├── connectors/
    │   └── analytics/
    ├── entities/
    ├── widgets/
    │   ├── app-shell/
    │   ├── sidebar/
    │   └── citation-panel/
    └── shared/
        ├── ui/                 # shadcn
        ├── api/                # axios + react-query
        ├── lib/
        ├── hooks/
        └── types/
```

---

## 11.4 Naming

| Area | Convention |
|------|------------|
| Python | snake_case modules, PascalCase classes |
| TS/React | PascalCase components, camelCase vars |
| API paths | plural kebab-case nouns |
| Tables | plural snake_case |
| Env vars | SCREAMING_SNAKE_CASE (`EAW_` prefix optional) |

---

**Next:** [12-AUTH-RAG-INTEGRATIONS.md](./12-AUTH-RAG-INTEGRATIONS.md)
