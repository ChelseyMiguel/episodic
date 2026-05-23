from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    contributors,
    submissions,
    editorial,
    articles,
    issues,
    resources,
    reports,
    newsletter,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(contributors.router)
api_router.include_router(submissions.router)
api_router.include_router(editorial.router)
api_router.include_router(articles.router)
api_router.include_router(issues.router)
api_router.include_router(resources.router)
api_router.include_router(reports.router)
api_router.include_router(newsletter.router)
