from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
import asyncio
import time
import httpx
import redis.asyncio as redis
from qdrant_client import QdrantClient

from src.database.connection import get_session
from src.core.config import get_settings
from src.core.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("/", response_model=Dict[str, Any])
async def health_check(db: AsyncSession = Depends(get_session)):
    """Comprehensive health check for all services."""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.version,
        "environment": settings.environment,
        "services": {},
        "response_time": 0
    }
    
    # Database health
    try:
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        health_status["services"]["database"] = {
            "status": "healthy",
            "url": settings.database_url.split("@")[1] if "@" in settings.database_url else "configured"
        }
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Redis health
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        health_status["services"]["redis"] = {
            "status": "healthy",
            "url": settings.redis_url
        }
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Qdrant health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.qdrant_url}/health", timeout=5.0)
            if response.status_code == 200:
                health_status["services"]["qdrant"] = {
                    "status": "healthy",
                    "url": settings.qdrant_url
                }
            else:
                raise Exception(f"HTTP {response.status_code}")
    except Exception as e:
        health_status["services"]["qdrant"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Ollama health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                health_status["services"]["ollama"] = {
                    "status": "healthy",
                    "url": settings.ollama_url,
                    "models_available": len(models)
                }
            else:
                raise Exception(f"HTTP {response.status_code}")
    except Exception as e:
        health_status["services"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Gemini API health (basic check)
    if settings.gemini_api_key:
        health_status["services"]["gemini"] = {
            "status": "configured",
            "api_key_configured": True
        }
    else:
        health_status["services"]["gemini"] = {
            "status": "not_configured",
            "api_key_configured": False
        }
    
    health_status["response_time"] = round((time.time() - start_time) * 1000, 2)  # ms
    
    # Determine overall status
    if all(service.get("status") == "healthy" for service in health_status["services"].values()):
        health_status["status"] = "healthy"
    elif any(service.get("status") == "unhealthy" for service in health_status["services"].values()):
        health_status["status"] = "unhealthy"
    
    logger.info("Health check completed", 
                status=health_status["status"], 
                response_time=health_status["response_time"])
    
    # Return appropriate HTTP status
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready")
async def readiness_check():
    """Simple readiness check for load balancers."""
    return {"status": "ready", "timestamp": time.time()}


@router.get("/live")
async def liveness_check():
    """Simple liveness check for container orchestration."""
    return {"status": "alive", "timestamp": time.time()}