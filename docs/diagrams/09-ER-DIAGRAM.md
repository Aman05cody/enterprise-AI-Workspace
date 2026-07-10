# 9. ER Diagram

| Field | Value |
|-------|--------|
| Document ID | EAW-ER-001 |
| Version | 1.0.0 |

---

## 9.1 Entity Relationship Diagram

```mermaid
erDiagram
  users ||--o{ oauth_accounts : has
  users ||--o{ refresh_tokens : has
  users ||--o{ email_verification_tokens : has
  users ||--o{ password_reset_tokens : has
  users ||--o{ memberships : joins
  users ||--o{ invites : sends
  users ||--o{ documents : uploads
  users ||--o{ conversations : owns
  users ||--o{ message_feedback : rates
  users ||--o{ audit_logs : acts

  organizations ||--o{ memberships : has
  organizations ||--o{ departments : has
  organizations ||--o{ invites : issues
  organizations ||--o{ knowledge_bases : owns
  organizations ||--o{ documents : scopes
  organizations ||--o{ conversations : scopes
  organizations ||--o{ connectors : owns
  organizations ||--o{ usage_events : tracks
  organizations ||--o{ audit_logs : tracks
  organizations ||--|| organization_usage_counters : aggregates

  departments ||--o{ membership_departments : includes
  memberships ||--o{ membership_departments : assigned
  departments ||--o{ knowledge_bases : scopes

  knowledge_bases ||--o{ documents : contains
  knowledge_bases ||--o{ conversations : powers

  documents ||--o{ document_versions : versions
  documents ||--o{ document_chunks : splits
  documents ||--o{ ingestion_jobs : processes
  documents ||--o{ message_citations : cited

  document_chunks ||--o{ message_citations : referenced

  conversations ||--o{ messages : contains
  messages ||--o{ message_citations : has
  messages ||--o{ message_feedback : receives

  connectors ||--o{ connector_resources : manages
  connectors ||--o{ connector_sync_jobs : runs

  users {
    uuid id PK
    citext email UK
    text password_hash
    varchar full_name
    timestamptz email_verified_at
  }

  organizations {
    uuid id PK
    varchar name
    varchar slug UK
    varchar plan_tier
    jsonb settings
  }

  departments {
    uuid id PK
    uuid organization_id FK
    varchar name
  }

  memberships {
    uuid id PK
    uuid organization_id FK
    uuid user_id FK
    varchar role
    varchar status
  }

  knowledge_bases {
    uuid id PK
    uuid organization_id FK
    uuid department_id FK
    varchar name
  }

  documents {
    uuid id PK
    uuid organization_id FK
    uuid knowledge_base_id FK
    varchar status
    int current_version
    varchar source_type
  }

  document_versions {
    uuid id PK
    uuid document_id FK
    int version_number
    text storage_key
  }

  document_chunks {
    uuid id PK
    uuid document_id FK
    int chunk_index
    text content
  }

  conversations {
    uuid id PK
    uuid organization_id FK
    uuid user_id FK
    text memory_summary
  }

  messages {
    uuid id PK
    uuid conversation_id FK
    varchar role
    text content
    float confidence
  }

  message_citations {
    uuid id PK
    uuid message_id FK
    uuid document_id FK
    uuid chunk_id FK
    text excerpt
  }

  connectors {
    uuid id PK
    uuid organization_id FK
    varchar type
    varchar status
  }

  connector_resources {
    uuid id PK
    uuid connector_id FK
    varchar external_id
    varchar resource_type
  }

  usage_events {
    uuid id PK
    uuid organization_id FK
    varchar event_type
    int input_tokens
    int output_tokens
  }

  audit_logs {
    uuid id PK
    uuid organization_id FK
    varchar action
    jsonb metadata
  }
```

---

## 9.2 Tenant Isolation View

```mermaid
flowchart TB
  Org[organizations]
  Org --> Mem[memberships]
  Org --> Dept[departments]
  Org --> KB[knowledge_bases]
  Org --> Conn[connectors]
  KB --> Doc[documents]
  Doc --> Ver[document_versions]
  Doc --> Chunk[document_chunks]
  Doc --> Job[ingestion_jobs]
  Org --> Conv[conversations]
  Conv --> Msg[messages]
  Msg --> Cite[message_citations]
  Conn --> Res[connector_resources]
```

**Invariant:** Every read/write path for tenant data validates membership and applies `organization_id` predicates.

---

**Next:** [../architecture/10-API-DESIGN.md](../architecture/10-API-DESIGN.md)
