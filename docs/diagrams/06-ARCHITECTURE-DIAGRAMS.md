# 6. Architecture Diagrams (Mermaid)

| Field | Value |
|-------|--------|
| Document ID | EAW-DIAG-001 |
| Version | 1.0.0 |

---

## 6.1 System Context

```mermaid
flowchart TB
  Employee([Employee])
  Manager([Manager])
  Admin([Admin / Owner])

  EAW[Enterprise AI Workspace]

  Google[Google OAuth]
  GitHubId[GitHub OAuth]
  LLM[LLM Providers]
  S3[S3-Compatible Storage]
  GH[GitHub API]
  Notion[Notion API]
  Jira[Jira API]
  Slack[Slack API]
  Drive[Google Drive API]
  Email[Email Provider]

  Employee --> EAW
  Manager --> EAW
  Admin --> EAW

  EAW --> Google
  EAW --> GitHubId
  EAW --> LLM
  EAW --> S3
  EAW --> Email
  EAW -.-> GH
  EAW -.-> Notion
  EAW -.-> Jira
  EAW -.-> Slack
  EAW -.-> Drive
```

---

## 6.2 Container Architecture

```mermaid
flowchart TB
  Browser[Web Browser]

  subgraph Edge
    Nginx[Nginx]
  end

  subgraph App
    Web[Next.js Web]
    API[FastAPI API]
    Worker[Celery Workers]
    Beat[Celery Beat optional]
  end

  subgraph Data
    PG[(PostgreSQL)]
    Redis[(Redis)]
    Qdrant[(Qdrant)]
    Obj[Object Storage]
  end

  subgraph External
    OAuth[OAuth Providers]
    LLM[LLM / Embeddings]
    Connectors[External SaaS APIs]
  end

  Browser --> Nginx
  Nginx --> Web
  Nginx --> API
  Web --> API
  API --> PG
  API --> Redis
  API --> Qdrant
  API --> Obj
  API --> OAuth
  API --> LLM
  Worker --> Redis
  Worker --> PG
  Worker --> Qdrant
  Worker --> Obj
  Worker --> LLM
  Worker --> Connectors
  Beat --> Redis
```

---

## 6.3 Clean Architecture (Backend)

```mermaid
flowchart LR
  subgraph API
    R[Routers]
    DTO[Schemas]
    MW[Auth Middleware]
  end

  subgraph Application
    UC[Use Cases]
    Ports[Ports]
  end

  subgraph Domain
    Ent[Entities]
    Pol[Policies]
  end

  subgraph Infra
    Repo[SQLAlchemy Repos]
    V[Qdrant]
    S[S3]
    L[LLM Adapters]
    C[Connectors]
    Q[Celery Tasks]
  end

  R --> UC
  MW --> R
  DTO --> R
  UC --> Ports
  UC --> Ent
  UC --> Pol
  Repo -.->|implements| Ports
  V -.->|implements| Ports
  S -.->|implements| Ports
  L -.->|implements| Ports
  C -.->|implements| Ports
  Q --> UC
```

---

## 6.4 Sequence — Grounded Chat (SSE)

```mermaid
sequenceDiagram
  autonumber
  actor U as User
  participant W as Web
  participant A as API
  participant DB as PostgreSQL
  participant V as Qdrant
  participant RR as Reranker
  participant CC as Compressor
  participant L as LLM

  U->>W: Ask question
  W->>A: POST messages:stream
  A->>A: JWT + RBAC + rate limit
  A->>DB: Load conversation + memory summary
  A->>V: Hybrid search filtered by org/ACL
  V-->>A: Candidates
  A->>RR: Cross-encoder rerank
  RR-->>A: Top-N
  A->>CC: Compress context
  alt Insufficient context
    A-->>W: Refuse + low confidence
  else Sufficient context
    A->>L: Stream completion
    loop tokens
      L-->>A: delta
      A-->>W: SSE token
    end
    A->>DB: Save message, citations, usage
    A-->>W: SSE citations + confidence + done
  end
```

---

## 6.5 Sequence — Document Ingestion

```mermaid
sequenceDiagram
  autonumber
  actor U as User
  participant A as API
  participant S as S3
  participant DB as PostgreSQL
  participant Q as Redis/Celery
  participant W as Worker
  participant E as Embeddings
  participant V as Qdrant

  U->>A: Upload file
  A->>A: Validate type/size/RBAC
  A->>S: Put object
  A->>DB: document=pending + version
  A->>Q: enqueue ingest
  A-->>U: 202 Accepted
  W->>DB: processing
  W->>S: Get object
  W->>W: Extract → Clean → OCR? → Chunk
  W->>E: Embed chunks
  W->>V: Upsert vectors + payload
  W->>DB: chunks + ready/failed + progress
```

---

## 6.6 RAG Pipeline Architecture

```mermaid
flowchart TD
  A[Upload / Connector Sync] --> B[Extraction]
  B --> C[Cleaning]
  C --> D{Scanned / low text?}
  D -->|yes| E[OCR]
  D -->|no| F[Chunking]
  E --> F
  F --> G[Embedding]
  G --> H[Qdrant Upsert]
  H --> I[Indexed Knowledge]

  J[User Query] --> K[Query Embedding + Keywords]
  K --> L[Hybrid Retrieval]
  I --> L
  L --> M[Cross-Encoder Re-rank]
  M --> N[Context Compression]
  N --> O{Confidence / relevance OK?}
  O -->|no| P[Refuse / Insufficient Context]
  O -->|yes| Q[LLM Grounded Generation]
  Q --> R[Answer + Citations + Confidence]
```

---

## 6.7 Deployment Nodes

```mermaid
flowchart TB
  Users[Users] --> NX[Nginx TLS]
  NX --> WEB[web]
  NX --> API[api]
  API --> PG[(postgres)]
  API --> RD[(redis)]
  API --> QD[(qdrant)]
  API --> ST[object storage]
  WRK[worker x N] --> PG
  WRK --> RD
  WRK --> QD
  WRK --> ST
```

---

**Next:** [07-USE-CASE-DIAGRAM.md](./07-USE-CASE-DIAGRAM.md)
