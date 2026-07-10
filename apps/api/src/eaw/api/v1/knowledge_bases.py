"""Knowledge base routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Request

from eaw.api.deps import CurrentUser, KnowledgeSvc
from eaw.api.schemas.common import DataResponse, MessageResponse, Meta
from eaw.api.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
)

router = APIRouter(tags=["knowledge-bases"])


def _kb_out(kb, stats: Optional[dict] = None) -> KnowledgeBaseOut:
    return KnowledgeBaseOut(
        id=kb.id,
        organization_id=kb.organization_id,
        department_id=kb.department_id,
        name=kb.name,
        description=kb.description,
        settings=kb.settings or {},
        stats=stats,
        created_at=kb.created_at,
    )


@router.post("/knowledge-bases", response_model=DataResponse[KnowledgeBaseOut], status_code=201)
def create_kb(
    body: KnowledgeBaseCreate,
    request: Request,
    user: CurrentUser,
    kb_svc: KnowledgeSvc,
) -> DataResponse[KnowledgeBaseOut]:
    kb = kb_svc.create(
        organization_id=body.organization_id,
        user_id=user.id,
        name=body.name,
        description=body.description,
        department_id=body.department_id,
    )
    return DataResponse(
        data=_kb_out(kb, stats={"document_count": 0, "by_status": {}}),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/knowledge-bases", response_model=DataResponse[list[KnowledgeBaseOut]])
def list_kbs(
    request: Request,
    user: CurrentUser,
    kb_svc: KnowledgeSvc,
    organization_id: UUID = Query(...),
) -> DataResponse[list[KnowledgeBaseOut]]:
    rows = kb_svc.list(organization_id=organization_id, user_id=user.id)
    data = [_kb_out(kb, stats) for kb, stats in rows]
    return DataResponse(
        data=data,
        meta=Meta(
            request_id=getattr(request.state, "request_id", None),
            total=len(data),
        ),
    )


@router.get("/knowledge-bases/{kb_id}", response_model=DataResponse[KnowledgeBaseOut])
def get_kb(
    kb_id: UUID,
    request: Request,
    user: CurrentUser,
    kb_svc: KnowledgeSvc,
) -> DataResponse[KnowledgeBaseOut]:
    kb, stats = kb_svc.get(kb_id=kb_id, user_id=user.id)
    return DataResponse(
        data=_kb_out(kb, stats),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get("/knowledge-bases/{kb_id}/stats", response_model=DataResponse[dict])
def kb_stats(
    kb_id: UUID,
    request: Request,
    user: CurrentUser,
    kb_svc: KnowledgeSvc,
) -> DataResponse[dict]:
    _, stats = kb_svc.get(kb_id=kb_id, user_id=user.id)
    return DataResponse(
        data=stats,
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch("/knowledge-bases/{kb_id}", response_model=DataResponse[KnowledgeBaseOut])
def update_kb(
    kb_id: UUID,
    body: KnowledgeBaseUpdate,
    request: Request,
    user: CurrentUser,
    kb_svc: KnowledgeSvc,
) -> DataResponse[KnowledgeBaseOut]:
    kb = kb_svc.update(
        kb_id=kb_id,
        user_id=user.id,
        name=body.name,
        description=body.description,
        department_id=body.department_id,
        settings=body.settings,
    )
    _, stats = kb_svc.get(kb_id=kb.id, user_id=user.id)
    return DataResponse(
        data=_kb_out(kb, stats),
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )


@router.delete("/knowledge-bases/{kb_id}", response_model=MessageResponse)
def delete_kb(
    kb_id: UUID,
    request: Request,
    user: CurrentUser,
    kb_svc: KnowledgeSvc,
) -> MessageResponse:
    kb_svc.soft_delete(kb_id=kb_id, user_id=user.id)
    return MessageResponse(
        data={"ok": True},
        meta=Meta(request_id=getattr(request.state, "request_id", None)),
    )
