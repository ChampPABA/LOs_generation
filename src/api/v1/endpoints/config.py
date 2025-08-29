"""
Configuration management endpoints for runtime configuration and validation.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from ...core.config_manager import config_manager, Environment
from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/validate")
async def validate_configuration():
    """
    Validate current configuration against environment requirements.
    
    Returns:
        Configuration validation results with errors, warnings, and recommendations
    """
    try:
        validation = config_manager.validate_configuration()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": config_manager.environment.value,
            "is_valid": validation.is_valid,
            "validation_results": {
                "errors": validation.errors,
                "warnings": validation.warnings,
                "recommendations": validation.recommendations
            },
            "summary": {
                "error_count": len(validation.errors),
                "warning_count": len(validation.warnings),
                "recommendation_count": len(validation.recommendations)
            }
        }
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration"
        )


@router.get("/summary")
async def get_configuration_summary():
    """
    Get comprehensive configuration summary.
    
    Returns:
        Complete configuration summary with validation and deployment checklist
    """
    try:
        summary = config_manager.export_config_summary()
        summary["timestamp"] = datetime.utcnow().isoformat()
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get configuration summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration summary"
        )


@router.get("/deployment-checklist")
async def get_deployment_checklist():
    """
    Get deployment checklist for current environment.
    
    Returns:
        Environment-specific deployment checklist
    """
    try:
        checklist = config_manager.generate_deployment_checklist()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": config_manager.environment.value,
            "checklist": checklist,
            "total_items": len(checklist)
        }
        
    except Exception as e:
        logger.error(f"Failed to get deployment checklist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate deployment checklist"
        )


@router.get("/environment/{env_name}/template")
async def get_environment_template(env_name: str):
    """
    Get configuration template for specific environment.
    
    Args:
        env_name: Environment name (development, testing, staging, production)
    
    Returns:
        Environment-specific configuration template
    """
    try:
        # Validate environment name
        try:
            environment = Environment(env_name.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid environment: {env_name}. Valid options: {[e.value for e in Environment]}"
            )
        
        template = config_manager.create_environment_config(environment)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": environment.value,
            "template": template,
            "description": f"Configuration template for {environment.value} environment"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get environment template for {env_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate environment template"
        )


@router.get("/current")
async def get_current_configuration():
    """
    Get current configuration (safe values only, no secrets).
    
    Returns:
        Current configuration with sensitive values masked
    """
    try:
        settings = get_settings()
        
        # Create safe configuration (mask sensitive values)
        safe_config = {
            "app_name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "debug": settings.debug,
            "database": {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "url_masked": _mask_url(settings.database_url)
            },
            "redis": {
                "max_connections": settings.redis_max_connections,
                "url_masked": _mask_url(settings.redis_url)
            },
            "qdrant": {
                "collection_name": settings.qdrant_collection_name,
                "vector_dimension": settings.vector_dimension,
                "url_masked": _mask_url(settings.qdrant_url)
            },
            "apis": {
                "ollama_url_masked": _mask_url(settings.ollama_url),
                "gemini_api_key_masked": _mask_api_key(settings.gemini_api_key),
                "langfuse_configured": bool(settings.langfuse_public_key)
            },
            "rate_limiting": {
                "default_rate_limit": settings.default_rate_limit,
                "rate_limit_period": settings.rate_limit_period,
                "api_rate_limit_per_minute": settings.api_rate_limit_per_minute,
                "api_rate_limit_per_hour": settings.api_rate_limit_per_hour
            },
            "security": {
                "force_https": settings.force_https,
                "ssl_configured": bool(settings.ssl_cert_path and settings.ssl_key_path),
                "allowed_hosts_count": len(settings.allowed_hosts),
                "cors_origins_count": len(settings.cors_origins)
            },
            "processing": {
                "max_concurrent_jobs": settings.max_concurrent_jobs,
                "chunk_size": settings.chunk_size,
                "overlap_size": settings.overlap_size,
                "max_retrieval_chunks": settings.max_retrieval_chunks,
                "top_k_retrieval": settings.top_k_retrieval
            },
            "models": {
                "default_embedding_model": settings.default_embedding_model,
                "english_embedding_model": settings.english_embedding_model,
                "thai_reranker_model": settings.thai_reranker_model,
                "english_reranker_model": settings.english_reranker_model
            },
            "logging": {
                "log_level": settings.log_level,
                "log_format": settings.log_format
            }
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": safe_config,
            "note": "Sensitive values are masked for security"
        }
        
    except Exception as e:
        logger.error(f"Failed to get current configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve current configuration"
        )


def _mask_url(url: str) -> str:
    """Mask sensitive parts of URLs."""
    if not url:
        return "[not configured]"
    
    # Mask passwords in URLs
    if "@" in url:
        parts = url.split("@")
        if len(parts) == 2:
            prefix = parts[0]
            if "://" in prefix:
                protocol, credentials = prefix.split("://", 1)
                if ": " in credentials:
                    user, _ = credentials.split(":", 1)
                    return f"{protocol}://{user}:***@{parts[1]}"
    
    return url


def _mask_api_key(api_key: str) -> str:
    """Mask API keys for display."""
    if not api_key or len(api_key) < 8:
        return "[not configured]"
    
    return f"{api_key[:4]}...{api_key[-4:]}"
