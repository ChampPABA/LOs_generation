"""
Monitoring endpoints for system health, metrics, and circuit breaker status.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from ...api.circuit_breaker import circuit_registry
from ...core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/circuit-breakers", response_model=Dict[str, Dict[str, Any]])
async def get_circuit_breakers_status():
    """
    Get status of all circuit breakers in the system.
    
    Returns:
        Dictionary mapping circuit breaker names to their statistics
    """
    try:
        stats = await circuit_registry.get_all_stats()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breakers": stats
        }
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker status"
        )


@router.post("/circuit-breakers/{breaker_name}/reset")
async def reset_circuit_breaker(breaker_name: str):
    """
    Reset a specific circuit breaker to closed state.
    
    Args:
        breaker_name: Name of the circuit breaker to reset
    """
    try:
        # Get the circuit breaker
        breaker = await circuit_registry.get_or_create(breaker_name)
        await breaker.reset()
        
        logger.info(f"Circuit breaker '{breaker_name}' has been reset")
        return {
            "message": f"Circuit breaker '{breaker_name}' has been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker '{breaker_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker '{breaker_name}'"
        )


@router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers():
    """
    Reset all circuit breakers to closed state.
    """
    try:
        await circuit_registry.reset_all()
        
        logger.info("All circuit breakers have been reset")
        return {
            "message": "All circuit breakers have been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to reset all circuit breakers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset all circuit breakers"
        )


@router.get("/system-status")
async def get_system_status():
    """
    Get overall system status including circuit breakers.
    """
    try:
        circuit_stats = await circuit_registry.get_all_stats()
        
        # Count circuit breaker states
        breaker_summary = {
            "total": len(circuit_stats),
            "closed": 0,
            "open": 0,
            "half_open": 0
        }
        
        for stats in circuit_stats.values():
            state = stats.get("state", "unknown")
            if state in breaker_summary:
                breaker_summary[state] += 1
        
        # Determine overall health
        overall_health = "healthy"
        if breaker_summary["open"] > 0:
            overall_health = "degraded"
        elif breaker_summary["half_open"] > 0:
            overall_health = "recovering"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health": overall_health,
            "circuit_breakers": breaker_summary,
            "details": circuit_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system status"
        )
