"""Document management routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import Response

from eaw.api.deps import CurrentUser, DocumentSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.knowledge import (
    DocumentOut,
    DocumentPreviewOut,
    DocumentSearchHit,
    DocumentVersionOut,
    SearchRequest,
)
from eaw.domain.common.errors import ValidationAppError

router = APIRouter(tags=["documents"])


def _doc_out(doc) -> DocumentOut:
    return DocumentOut.model_validate(doc)


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DataResponse[list[DocumentOut]],
)
def list_documents(
    kb_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> DataResponse[list[DocumentOut]]:
    docs, total = doc_svc.list_documents(
        kb_id=kb_id,
        user_id=user.id,
        status=status,
        q=q,
        limit=limit,
        offset=offset,
    )
    return DataResponse(
        data=[_doc_out(d) for d in docs],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            page=offset // limit + 1 if limit else 1,
            page_size=limit,
            total=total,
        ),
    )


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DataResponse[DocumentOut],
    status_code=201,
)
async def upload_document(
    kb_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
) -> DataResponse[DocumentOut]:
    if not file.filename:
        raise ValidationAppError("Filename is required")
    data = await file.read()
    doc = doc_svc.upload(
        kb_id=kb_id,
        user_id=user.id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        title=title,
    )
    return DataResponse(
        data=_doc_out(doc),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/documents/{document_id}", response_model=DataResponse[DocumentOut])
def get_document(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> DataResponse[DocumentOut]:
    doc = doc_svc.get_document(document_id=document_id, user_id=user.id)
    return DataResponse(
        data=_doc_out(doc),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/documents/{document_id}/preview",
    response_model=DataResponse[DocumentPreviewOut],
)
def preview_document(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> DataResponse[DocumentPreviewOut]:
    preview = doc_svc.get_preview(document_id=document_id, user_id=user.id)
    return DataResponse(
        data=DocumentPreviewOut(**preview),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/documents/{document_id}/versions",
    response_model=DataResponse[list[DocumentVersionOut]],
)
def list_versions(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> DataResponse[list[DocumentVersionOut]]:
    versions = doc_svc.list_versions(document_id=document_id, user_id=user.id)
    return DataResponse(
        data=[DocumentVersionOut.model_validate(v) for v in versions],
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(versions),
        ),
    )


@router.post(
    "/documents/{document_id}/versions",
    response_model=DataResponse[DocumentOut],
    status_code=201,
)
async def upload_version(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
    file: UploadFile = File(...),
) -> DataResponse[DocumentOut]:
    if not file.filename:
        raise ValidationAppError("Filename is required")
    data = await file.read()
    doc = doc_svc.upload_new_version(
        document_id=document_id,
        user_id=user.id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )
    return DataResponse(
        data=_doc_out(doc),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: UUID,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> MessageResponse:
    doc_svc.soft_delete(document_id=document_id, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> Response:
    doc, data = doc_svc.download(document_id=document_id, user_id=user.id)
    return Response(
        content=data,
        media_type=doc.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"'
        },
    )


@router.post(
    "/organizations/{org_id}/documents/search",
    response_model=DataResponse[list[DocumentSearchHit]],
)
def search_documents(
    org_id: UUID,
    body: SearchRequest,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> DataResponse[list[DocumentSearchHit]]:
    docs = doc_svc.search_workspace(
        organization_id=org_id,
        user_id=user.id,
        query=body.query,
        knowledge_base_id=body.knowledge_base_id,
        limit=body.limit,
    )
    hits = []
    for d in docs:
        snippet = None
        if d.preview_text:
            snippet = d.preview_text[:240]
        hits.append(DocumentSearchHit(document=_doc_out(d), snippet=snippet))
    return DataResponse(
        data=hits,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(hits),
        ),
    )


@router.post(
    "/knowledge-bases/{kb_id}/search",
    response_model=DataResponse[list[DocumentSearchHit]],
)
def search_kb(
    kb_id: UUID,
    body: SearchRequest,
    request: Request,
    user: CurrentUser,
    doc_svc: DocumentSvc,
) -> DataResponse[list[DocumentSearchHit]]:
    docs, _ = doc_svc.list_documents(
        kb_id=kb_id, user_id=user.id, q=body.query, limit=body.limit
    )
    hits = [
        DocumentSearchHit(
            document=_doc_out(d),
            snippet=(d.preview_text[:240] if d.preview_text else None),
        )
        for d in docs
    ]
    return DataResponse(
        data=hits,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(hits),
        ),
    )
