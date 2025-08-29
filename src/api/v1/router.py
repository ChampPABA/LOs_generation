from fastapi import APIRouter
from .endpoints import health, learning_objectives, content, jobs, rate_limits, monitoring, config

api_v1_router = APIRouter()

# Include routers
api_v1_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_v1_router.include_router(
    learning_objectives.router,
    prefix="/learning-objectives", 
    tags=["Learning Objectives Generation"]
)

api_v1_router.include_router(
    content.router,
    prefix="/content",
    tags=["Hybrid Content Processing"]
)

api_v1_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["Enhanced Job Management"]
)

api_v1_router.include_router(
    rate_limits.router,
    prefix="/rate-limits",
    tags=["Rate Limiting & Usage Monitoring"]
)

api_v1_router.include_router(
    monitoring.router,
    tags=["System Monitoring"]
)

api_v1_router.include_router(
    config.router,
    tags=["Configuration Management"]
)

# Legacy endpoint redirects for backward compatibility
api_v1_router.include_router(
    learning_objectives.router,
    prefix="/generate-los",
    tags=["Legacy Endpoints"],
    deprecated=True
)