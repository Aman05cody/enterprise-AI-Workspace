"""Ingestion job and semantic search routes."""

from uuid import UUID

from fastapi import APIRouter, Request

from eaw.api.deps import CurrentUser, DocumentSvc, IngestionSvc, RetrievalSvc
from eaw.api.schemas.common import DataResponse, Meta
from eaw.api.schemas.ingestion import (
    IngestionJobOut,
    SemanticSearchHit,
    SemanticSearchRequest,
)
from eaw.infrastructure.queue.enqueue import enqueue_ingestion_job

router = APIRouter(tags=["ingestion"])


@router.get(
    "/documents/{document_id}/jobs",
    response_model=DataResponse[list[IngestionJobOut]],
)
def list_jobs(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
    ing_svc: IngestionSvc,
) -> DataResponse[list[IngestionJobOut]]:
    # Auth via document access
    doc_svc.get_document(document_id=document_id, user_id=user.id)
    jobs = ing_svc.list_jobs(document_id)
    return DataResponse(
        data=[IngestionJobOut.model_validate(j) for j in jobs],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(jobs),
        ),
    )


@router.get("/ingestion-jobs/{job_id}", response_model=DataResponse[IngestionJobOut])
def get_job(
    job_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
    ing_svc: IngestionSvc,
) -> DataResponse[IngestionJobOut]:
    job = ing_svc.get_job(job_id)
    doc_svc.get_document(document_id=job.document_id, user_id=user.id)
    return DataResponse(
        data=IngestionJobOut.model_validate(job),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=DataResponse[IngestionJobOut],
    status_code=202,
)
def reprocess(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    ing_svc: IngestionSvc,
) -> DataResponse[IngestionJobOut]:
    job = ing_svc.reprocess(document_id=document_id, user_id=user.id)
    task_id = enqueue_ingestion_job(job.id)
    if task_id:
        job.celery_task_id = task_id
        ing_svc.db.commit()
    # Re-load after sync pipeline may have completed in another session
    job = ing_svc.get_job(job.id)
    return DataResponse(
        data=IngestionJobOut.model_validate(job),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/knowledge-bases/{kb_id}/semantic-search",
    response_model=DataResponse[list[SemanticSearchHit]],
)
def semantic_search(
    kb_id: UUID,
    body: SemanticSearchRequest,
    request: Request,
    user: CurrentUser,
    retrieval: RetrievalSvc,
) -> DataResponse[list[SemanticSearchHit]]:
    hits = retrieval.semantic_search(
        kb_id=kb_id,
        user_id=user.id,
        query=body.query,
        top_k=body.top_k,
    )
    data = [
        SemanticSearchHit(
            chunk_id=h.id,
            score=h.score,
            document_id=h.payload.get("document_id"),
            title=h.payload.get("title"),
            content_preview=h.payload.get("content_preview"),
            chunk_index=h.payload.get("chunk_index"),
        )
        for h in hits
    ]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(data),
        ),
    )
