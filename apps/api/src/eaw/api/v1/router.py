"""API v1 router aggregate."""

from fastapi import APIRouter

from eaw.api.v1 import (
    analytics,
    auth,
    chat,
    documents,
    drive,
    github,
    ingestion,
    jira,
    knowledge_bases,
    notion,
    organizations,
    slack,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(knowledge_bases.router)
api_router.include_router(documents.router)
api_router.include_router(ingestion.router)
api_router.include_router(chat.router)
api_router.include_router(github.router)
api_router.include_router(notion.router)
api_router.include_router(drive.router)
api_router.include_router(slack.router)
api_router.include_router(jira.router)
api_router.include_router(analytics.router)
