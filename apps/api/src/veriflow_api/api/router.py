from fastapi import APIRouter

from veriflow_api.api.routes import auth, documents, health, structured_content, workspaces
from veriflow_api.config import settings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(
    auth.router,
    prefix=settings.api_v1_prefix,
    tags=["authentication"],
)
api_router.include_router(
    workspaces.router,
    prefix=settings.api_v1_prefix,
    tags=["workspaces"],
)
api_router.include_router(
    documents.router,
    prefix=settings.api_v1_prefix,
    tags=["documents"],
)
api_router.include_router(
    structured_content.router,
    prefix=settings.api_v1_prefix,
    tags=["structured-content"],
)
