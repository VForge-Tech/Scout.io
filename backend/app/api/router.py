from fastapi import APIRouter

from app.api.endpoints import (
    admin,
    analytics,
    auth,
    chatbots,
    developer,
    knowledge_sources,
    organizations,
    policies,
    retrieval,
    sessions,
    widget_api,
    widgets,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(chatbots.router)
api_router.include_router(policies.router)
api_router.include_router(knowledge_sources.router)
api_router.include_router(analytics.router)
api_router.include_router(sessions.router)
api_router.include_router(widgets.router)
api_router.include_router(developer.router)
api_router.include_router(widget_api.router)
api_router.include_router(retrieval.router)
api_router.include_router(admin.router)
