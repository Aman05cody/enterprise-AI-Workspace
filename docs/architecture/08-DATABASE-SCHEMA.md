# 8. Database Schema

| Field | Value |
|-------|--------|
| Document ID | EAW-DB-001 |
| Version | 1.0.0 |
| Engine | PostgreSQL 16+ |
| Migrations | Alembic (implementation phases) |

---

## 8.1 Design Principles

1. UUID primary keys for external IDs  
2. `organization_id` on all tenant-owned rows  
3. Soft deletes via `deleted_at` for critical entities  
4. JSONB for flexible settings/metadata  
5. Refresh tokens stored as hashes only  
6. Vectors in Qdrant; chunk text metadata in PostgreSQL for citations  
7. Billing-ready columns without requiring a payment provider in early phases  
8. Connector tables normalized for multi-integration growth  

---

## 8.2 Enumerations

| Name | Values |
|------|--------|
| `role` | owner, admin, manager, employee, guest |
| `membership_status` | active, invited, disabled |
| `invite_status` | pending, accepted, expired, revoked |
| `document_status` | pending, processing, ready, failed, deleted |
| `job_status` | queued, running, succeeded, failed, cancelled |
| `message_role` | user, assistant, system |
| `auth_provider` | local, google, github |
| `source_type` | upload, github, notion, gdrive, slack, jira, email |
| `connector_status` | disconnected, connected, error, syncing |
| `plan_tier` | free, team, business, enterprise (billing-ready) |

---

## 8.3 Core Tables

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | CITEXT UNIQUE NOT NULL | |
| email_verified_at | TIMESTAMPTZ NULL | |
| password_hash | TEXT NULL | null if OAuth-only |
| full_name | VARCHAR(200) NOT NULL | |
| avatar_url | TEXT NULL | |
| is_active | BOOLEAN DEFAULT TRUE | |
| last_login_at | TIMESTAMPTZ NULL | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### `oauth_accounts`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK users | |
| provider | VARCHAR(32) | google/github |
| provider_user_id | VARCHAR(255) | |
| email | CITEXT NULL | |
| raw_profile | JSONB NULL | |
| created_at / updated_at | TIMESTAMPTZ | |
| UNIQUE(provider, provider_user_id) | | |

### `refresh_tokens`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| token_hash | CHAR(64) UNIQUE | sha256 |
| expires_at | TIMESTAMPTZ | |
| revoked_at | TIMESTAMPTZ NULL | |
| user_agent / ip_address | TEXT / INET | |
| created_at | TIMESTAMPTZ | |

### `email_verification_tokens` / `password_reset_tokens`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| token_hash | CHAR(64) UNIQUE | |
| expires_at | TIMESTAMPTZ | |
| used_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ | |

### `organizations` (workspaces)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR(200) | |
| slug | VARCHAR(100) UNIQUE | |
| logo_url | TEXT NULL | |
| settings | JSONB DEFAULT {} | AI defaults, limits |
| plan_tier | VARCHAR(32) DEFAULT 'free' | billing-ready |
| seat_limit | INT NULL | billing-ready |
| created_by | UUID FK users NULL | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### `departments`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| name | VARCHAR(120) | |
| description | TEXT NULL | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |
| UNIQUE(organization_id, name) | | |

### `memberships`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| user_id | UUID FK | |
| role | VARCHAR(32) | |
| status | VARCHAR(32) | |
| created_at / updated_at | TIMESTAMPTZ | |
| UNIQUE(organization_id, user_id) | | |

### `membership_departments`
| Column | Type | Notes |
|--------|------|-------|
| membership_id | UUID FK | |
| department_id | UUID FK | |
| PK(membership_id, department_id) | | |

### `invites`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| email | CITEXT | |
| role | VARCHAR(32) | |
| department_id | UUID NULL | |
| token_hash | CHAR(64) UNIQUE | |
| status | VARCHAR(32) | |
| invited_by | UUID FK | |
| expires_at | TIMESTAMPTZ | |
| accepted_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ | |

---

## 8.4 Knowledge Tables

### `knowledge_bases`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| department_id | UUID NULL | optional scope |
| name | VARCHAR(200) | |
| description | TEXT NULL | |
| settings | JSONB | chunking, models |
| created_by | UUID NULL | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### `documents`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| knowledge_base_id | UUID FK | |
| title | VARCHAR(500) | |
| original_filename | VARCHAR(500) | |
| content_type | VARCHAR(150) | |
| file_size_bytes | BIGINT | |
| checksum_sha256 | CHAR(64) | |
| storage_key | TEXT | |
| status | VARCHAR(32) | |
| error_message | TEXT NULL | |
| source_type | VARCHAR(32) DEFAULT 'upload' | |
| current_version | INT DEFAULT 1 | |
| page_count / token_count / chunk_count | INT | |
| embedding_model | VARCHAR(120) NULL | |
| ai_summary | TEXT NULL | |
| ai_tags | JSONB DEFAULT [] | |
| ocr_used | BOOLEAN DEFAULT FALSE | |
| uploaded_by | UUID NULL | |
| processed_at | TIMESTAMPTZ NULL | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### `document_versions`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| document_id | UUID FK | |
| organization_id | UUID | |
| version_number | INT | |
| storage_key | TEXT | |
| checksum_sha256 | CHAR(64) | |
| created_by | UUID NULL | |
| created_at | TIMESTAMPTZ | |
| UNIQUE(document_id, version_number) | | |

### `document_chunks`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | vector point id |
| organization_id | UUID | |
| knowledge_base_id | UUID | |
| document_id | UUID FK | |
| version_number | INT | |
| chunk_index | INT | |
| content | TEXT | citation body |
| token_count | INT NULL | |
| metadata | JSONB | page, heading, source refs |
| created_at | TIMESTAMPTZ | |
| UNIQUE(document_id, version_number, chunk_index) | | |

### `ingestion_jobs`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| document_id | UUID FK | |
| celery_task_id | VARCHAR(155) NULL | |
| status | VARCHAR(32) | |
| stage | VARCHAR(64) NULL | extract/clean/chunk/... |
| progress_pct | INT DEFAULT 0 | |
| attempt | INT DEFAULT 0 | |
| error_message | TEXT NULL | |
| metrics | JSONB DEFAULT {} | |
| started_at / finished_at | TIMESTAMPTZ | |
| created_at / updated_at | TIMESTAMPTZ | |

---

## 8.5 Conversation Tables

### `conversations`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| user_id | UUID | |
| knowledge_base_id | UUID NULL | null = multi-source later |
| title | VARCHAR(300) NULL | |
| memory_summary | TEXT NULL | long-term memory |
| model | VARCHAR(120) NULL | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### `messages`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| conversation_id | UUID FK | |
| role | VARCHAR(32) | |
| content | TEXT | |
| confidence | DOUBLE PRECISION NULL | assistant |
| token_count / latency_ms | INT NULL | |
| model | VARCHAR(120) NULL | |
| created_at | TIMESTAMPTZ | |

### `message_citations`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| message_id | UUID FK | |
| document_id | UUID NULL | |
| chunk_id | UUID NULL | |
| source_type | VARCHAR(32) | |
| external_ref | VARCHAR(255) NULL | issue key, path, etc. |
| score | DOUBLE PRECISION NULL | |
| excerpt | TEXT | |
| rank | INT | |

### `message_feedback`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| message_id | UUID FK | |
| user_id | UUID FK | |
| organization_id | UUID | |
| rating | SMALLINT | +1/-1 |
| comment | TEXT NULL | |
| created_at | TIMESTAMPTZ | |
| UNIQUE(message_id, user_id) | | |

---

## 8.6 Connector Tables

### `connectors`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| type | VARCHAR(32) | github/notion/... |
| status | VARCHAR(32) | |
| display_name | VARCHAR(200) | |
| credentials_ref | TEXT | secret ref / encrypted blob pointer |
| config | JSONB DEFAULT {} | |
| last_synced_at | TIMESTAMPTZ NULL | |
| created_by | UUID NULL | |
| created_at / updated_at | TIMESTAMPTZ | |

### `connector_resources`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| connector_id | UUID FK | |
| organization_id | UUID | |
| external_id | VARCHAR(255) | repo id, page id, channel id |
| name | VARCHAR(500) | |
| resource_type | VARCHAR(64) | repo/page/folder/channel/project |
| sync_enabled | BOOLEAN DEFAULT TRUE | |
| metadata | JSONB DEFAULT {} | |
| last_synced_at | TIMESTAMPTZ NULL | |
| UNIQUE(connector_id, external_id) | | |

### `connector_sync_jobs`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| connector_id | UUID FK | |
| status | VARCHAR(32) | |
| stats | JSONB DEFAULT {} | |
| error_message | TEXT NULL | |
| created_at / finished_at | TIMESTAMPTZ | |

---

## 8.7 Analytics, Audit, Billing Hooks

### `usage_events`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID | |
| user_id | UUID NULL | |
| department_id | UUID NULL | |
| event_type | VARCHAR(64) | chat, embed, upload, sync |
| model | VARCHAR(120) NULL | |
| input_tokens / output_tokens | INT NULL | |
| metadata | JSONB DEFAULT {} | |
| created_at | TIMESTAMPTZ | |

### `audit_logs`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID NULL | |
| actor_user_id | UUID NULL | |
| action | VARCHAR(100) | |
| resource_type / resource_id | VARCHAR / UUID | |
| ip_address / user_agent | INET / TEXT | |
| metadata | JSONB DEFAULT {} | |
| created_at | TIMESTAMPTZ | |

### `organization_usage_counters` (billing-ready)
| Column | Type | Notes |
|--------|------|-------|
| organization_id | UUID PK/FK | |
| period_start | DATE | |
| messages_count | BIGINT DEFAULT 0 | |
| tokens_in / tokens_out | BIGINT | |
| storage_bytes | BIGINT DEFAULT 0 | |
| updated_at | TIMESTAMPTZ | |

---

## 8.8 Qdrant Payload Schema

**Collection:** `eaw_chunks`

| Payload Field | Purpose |
|---------------|---------|
| organization_id | **required filter** |
| knowledge_base_id | filter |
| document_id | citation |
| version_number | active version |
| source_type | upload/github/... |
| department_id | optional ACL |
| title | display |
| path_or_uri | code path / URL |
| chunk_index | ordering |

**Rule:** every query filters `organization_id` (+ ACL fields).

---

## 8.9 Object Key Layout

```text
{organization_id}/{knowledge_base_id}/{document_id}/v{version}/{filename}
```

---

**Next:** [../diagrams/09-ER-DIAGRAM.md](../diagrams/09-ER-DIAGRAM.md)
