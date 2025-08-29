"""
Rate limiting API endpoints for monitoring and managing API usage.
Provides insights into current usage patterns and cost controls.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from src.core.dependencies import get_current_user
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Models
class RateLimitInfo(BaseModel):
    """Rate limit information for an endpoint or service."""
    limit: int
    remaining: int
    reset_time: datetime
    window_seconds: int

class UsageStats(BaseModel):
    """Usage statistics for monitoring."""
    requests_count: int
    tokens_consumed: int
    cost_usd: float
    time_period: str
    
class QuotaInfo(BaseModel):
    """Quota information and limits."""
    daily_requests: RateLimitInfo
    monthly_requests: RateLimitInfo
    daily_tokens: RateLimitInfo
    monthly_tokens: RateLimitInfo
    daily_cost: RateLimitInfo
    monthly_cost: RateLimitInfo

class ServiceLimits(BaseModel):
    """Service-specific rate limits."""
    ocr_processing: RateLimitInfo
    agentic_chunking: RateLimitInfo
    lo_generation: RateLimitInfo
    vector_embeddings: RateLimitInfo

@router.get("/status", response_model=Dict[str, Any])
async def get_rate_limit_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current rate limit status for the user.
    """
    try:
        logger.info(f"Rate limit status requested for user: {current_user.get('user_id', 'unknown')}")
        
        # Mock rate limit data
        # In real implementation, this would query Redis/database for actual usage
        current_time = datetime.utcnow()
        
        quota_info = QuotaInfo(
            daily_requests=RateLimitInfo(
                limit=1000,
                remaining=750,
                reset_time=current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
                window_seconds=86400
            ),
            monthly_requests=RateLimitInfo(
                limit=25000,
                remaining=18500,
                reset_time=current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32),
                window_seconds=2592000  # 30 days
            ),
            daily_tokens=RateLimitInfo(
                limit=100000,
                remaining=65000,
                reset_time=current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
                window_seconds=86400
            ),
            monthly_tokens=RateLimitInfo(
                limit=2500000,
                remaining=1850000,
                reset_time=current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32),
                window_seconds=2592000
            ),
            daily_cost=RateLimitInfo(
                limit=100,  # $100 daily limit
                remaining=75,  # $75 remaining
                reset_time=current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
                window_seconds=86400
            ),
            monthly_cost=RateLimitInfo(
                limit=2000,  # $2000 monthly limit
                remaining=1650,  # $1650 remaining
                reset_time=current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32),
                window_seconds=2592000
            )
        )
        
        service_limits = ServiceLimits(
            ocr_processing=RateLimitInfo(
                limit=100,  # 100 pages per hour
                remaining=85,
                reset_time=current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
                window_seconds=3600
            ),
            agentic_chunking=RateLimitInfo(
                limit=50,  # 50 documents per hour
                remaining=35,
                reset_time=current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
                window_seconds=3600
            ),
            lo_generation=RateLimitInfo(
                limit=200,  # 200 generation requests per hour
                remaining=150,
                reset_time=current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
                window_seconds=3600
            ),
            vector_embeddings=RateLimitInfo(
                limit=500,  # 500 embedding operations per hour
                remaining=420,
                reset_time=current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
                window_seconds=3600
            )
        )
        
        return {
            "user_id": current_user.get('user_id', 'demo_user'),
            "quota_info": quota_info,
            "service_limits": service_limits,
            "current_time": current_time,
            "warnings": [
                "Daily token usage at 65% - consider optimization"
            ] if quota_info.daily_tokens.remaining / quota_info.daily_tokens.limit < 0.4 else []
        }
        
    except Exception as e:
        logger.error(f"Rate limit status retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@router.get("/usage-history")
async def get_usage_history(
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$", description="Time period for usage history"),
    granularity: str = Query("1h", regex="^(5m|1h|1d)$", description="Data granularity"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get historical usage data for monitoring trends.
    """
    try:
        logger.info(f"Usage history requested: period={period}, granularity={granularity}")
        
        # Mock historical data
        # In real implementation, this would query time-series data
        import random
        from datetime import datetime, timedelta
        
        # Generate time points based on granularity
        if granularity == "5m":
            interval = timedelta(minutes=5)
            points = 12 if period == "1h" else 288  # 1h or 24h
        elif granularity == "1h":
            interval = timedelta(hours=1)
            points = 24 if period == "24h" else 168 if period == "7d" else 720  # 24h, 7d, or 30d
        else:  # 1d
            interval = timedelta(days=1)
            points = 7 if period == "7d" else 30  # 7d or 30d
        
        current_time = datetime.utcnow()
        usage_history = []
        
        for i in range(points):
            timestamp = current_time - (interval * i)
            usage_history.append(UsageStats(
                requests_count=random.randint(10, 100),
                tokens_consumed=random.randint(500, 5000),
                cost_usd=round(random.uniform(0.50, 8.00), 2),
                time_period=timestamp.isoformat()
            ))
        
        # Reverse to get chronological order
        usage_history.reverse()
        
        return {
            "period": period,
            "granularity": granularity,
            "data_points": len(usage_history),
            "usage_history": usage_history,
            "summary": {
                "total_requests": sum(u.requests_count for u in usage_history),
                "total_tokens": sum(u.tokens_consumed for u in usage_history),
                "total_cost_usd": sum(u.cost_usd for u in usage_history),
                "avg_requests_per_period": sum(u.requests_count for u in usage_history) / len(usage_history),
                "peak_usage_time": max(usage_history, key=lambda x: x.requests_count).time_period
            }
        }
        
    except Exception as e:
        logger.error(f"Usage history retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Usage history failed: {str(e)}")

@router.get("/cost-breakdown")
async def get_cost_breakdown(
    period: str = Query("24h", regex="^(24h|7d|30d)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed cost breakdown by service and operation type.
    """
    try:
        logger.info(f"Cost breakdown requested for period: {period}")
        
        # Mock cost breakdown data
        cost_breakdown = {
            "period": period,
            "total_cost_usd": 45.67,
            "service_costs": {
                "ocr_processing": {
                    "cost_usd": 12.34,
                    "percentage": 27.0,
                    "operations": 156,
                    "avg_cost_per_operation": 0.079
                },
                "agentic_chunking": {
                    "cost_usd": 18.90,
                    "percentage": 41.4,
                    "operations": 89,
                    "avg_cost_per_operation": 0.212
                },
                "lo_generation": {
                    "cost_usd": 11.23,
                    "percentage": 24.6,
                    "operations": 245,
                    "avg_cost_per_operation": 0.046
                },
                "vector_embeddings": {
                    "cost_usd": 3.20,
                    "percentage": 7.0,
                    "operations": 412,
                    "avg_cost_per_operation": 0.008
                }
            },
            "cost_trends": {
                "ocr_processing": "stable",
                "agentic_chunking": "increasing",
                "lo_generation": "decreasing",
                "vector_embeddings": "stable"
            },
            "optimization_suggestions": [
                "Consider batch processing for OCR operations",
                "Review agentic chunking parameters for cost efficiency",
                "Current vector embedding usage is optimal"
            ]
        }
        
        return cost_breakdown
        
    except Exception as e:
        logger.error(f"Cost breakdown retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cost breakdown failed: {str(e)}")

@router.post("/adjust-limits")
async def adjust_rate_limits(
    limit_adjustments: Dict[str, int],
    current_user: dict = Depends(get_current_user)
):
    """
    Adjust rate limits (admin functionality).
    """
    try:
        logger.info(f"Rate limit adjustment requested: {limit_adjustments}")
        
        # Validate user has admin permissions
        if not current_user.get('is_admin', False):
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Validate adjustment parameters
        valid_limits = ["daily_requests", "monthly_requests", "daily_tokens", "monthly_tokens", 
                       "daily_cost", "monthly_cost", "ocr_processing", "agentic_chunking", 
                       "lo_generation", "vector_embeddings"]
        
        invalid_limits = [limit for limit in limit_adjustments.keys() if limit not in valid_limits]
        if invalid_limits:
            raise HTTPException(status_code=400, detail=f"Invalid limit types: {invalid_limits}")
        
        # In real implementation, this would update the rate limiting configuration
        
        return {
            "message": "Rate limits adjusted successfully",
            "updated_limits": limit_adjustments,
            "effective_time": datetime.utcnow(),
            "updated_by": current_user.get('user_id', 'admin')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limit adjustment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Limit adjustment failed: {str(e)}")

@router.get("/alerts")
async def get_usage_alerts(
    active_only: bool = Query(True, description="Only return active alerts"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current usage alerts and notifications.
    """
    try:
        logger.info(f"Usage alerts requested, active_only: {active_only}")
        
        # Mock alert data
        alerts = [
            {
                "alert_id": "alert_001",
                "type": "usage_warning",
                "severity": "medium",
                "service": "agentic_chunking",
                "message": "Daily token usage at 85% of limit",
                "threshold": 0.85,
                "current_usage": 85000,
                "limit": 100000,
                "created_at": datetime.utcnow() - timedelta(hours=2),
                "active": True
            },
            {
                "alert_id": "alert_002", 
                "type": "cost_alert",
                "severity": "high",
                "service": "overall",
                "message": "Monthly cost approaching budget limit",
                "threshold": 0.90,
                "current_cost": 1800.0,
                "budget_limit": 2000.0,
                "created_at": datetime.utcnow() - timedelta(hours=1),
                "active": True
            },
            {
                "alert_id": "alert_003",
                "type": "rate_limit",
                "severity": "low",
                "service": "ocr_processing",
                "message": "OCR processing rate limit reached",
                "created_at": datetime.utcnow() - timedelta(hours=4),
                "resolved_at": datetime.utcnow() - timedelta(hours=3),
                "active": False
            }
        ]
        
        if active_only:
            alerts = [alert for alert in alerts if alert["active"]]
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "active_alerts": len([a for a in alerts if a["active"]]),
            "alert_summary": {
                "high_severity": len([a for a in alerts if a.get("severity") == "high" and a["active"]]),
                "medium_severity": len([a for a in alerts if a.get("severity") == "medium" and a["active"]]),
                "low_severity": len([a for a in alerts if a.get("severity") == "low" and a["active"]])
            }
        }
        
    except Exception as e:
        logger.error(f"Usage alerts retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Alerts retrieval failed: {str(e)}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Acknowledge a usage alert.
    """
    try:
        logger.info(f"Alert acknowledgment requested for: {alert_id}")
        
        # In real implementation, this would update the alert status
        
        return {
            "alert_id": alert_id,
            "status": "acknowledged",
            "acknowledged_by": current_user.get('user_id', 'user'),
            "acknowledged_at": datetime.utcnow(),
            "message": "Alert acknowledged successfully"
        }
        
    except Exception as e:
        logger.error(f"Alert acknowledgment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Alert acknowledgment failed: {str(e)}")