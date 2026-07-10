# Phase 4 Completion Report

| Field | Value |
|-------|--------|
| Phase | 4 — RAG Indexing |
| Status | Complete |
| Version | 0.4.0 |

## Pipeline

```
Upload → Job queued → Extract → Clean → Chunk → Embed → Vector upsert → Ready
```

### Components
- `IngestionService.run_pipeline`
- Celery task `eaw.ingest_document` (+ **sync fallback**)
- Chunker (`chunk_size` / `chunk_overlap` from KB settings or env)
- Embedding ports: `hash` (default offline), `openai`
- Vector ports: `memory` (default offline), `qdrant`
- Tables: `document_chunks`, `ingestion_jobs`
- Migration: `20260711_0003_phase4_ingestion`

### API
- `GET /documents/{id}/jobs` — job history + progress
- `GET /ingestion-jobs/{id}`
- `POST /documents/{id}/reprocess` — Manager+
- `POST /knowledge-bases/{id}/semantic-search` — dense retrieval

### Progress tracking
Job fields: `status`, `stage`, `progress_pct`, `metrics`, `error_message`

Stages: queued → extract → clean → chunk → embed → index → finalize

### Docker
- `worker` service: Celery with `INGESTION_MODE=async`, `VECTOR_STORE_BACKEND=qdrant`
- Shared upload volume between api and worker

### Local defaults (no Redis/Qdrant required)
```
INGESTION_MODE=sync
EMBEDDING_PROVIDER=hash
VECTOR_STORE_BACKEND=memory
```

## Deferred to Phase 5
- Cross-encoder re-ranking
- Context compression
- Streaming grounded chat + citations
- Conversation memory

## Stop gate
Wait for **NEXT PHASE**.
