"""
Custom middleware for the Learning Objectives Generation API.
Includes rate limiting, request tracking, and error handling.
"""

import time
import uuid
from typing import Callable, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import get_logger

logger = get_logger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with configurable limits per user/IP.
    """
    
    def __init__(self, app: Callable, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps per client
        self.minute_requests = defaultdict(deque)  # client_id -> timestamps
        self.hour_requests = defaultdict(deque)
        
        logger.info(f"Rate limiting enabled: {requests_per_minute}/min, {requests_per_hour}/hour")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        current_time = datetime.utcnow()
        
        # Check and update rate limits
        if self._is_rate_limited(client_id, current_time):
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute, {self.requests_per_hour} per hour",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self._record_request(client_id, current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        self._add_rate_limit_headers(response, client_id, current_time)
        
        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get user ID from auth context first
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.get('user_id', 'anonymous')}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"

    def _is_rate_limited(self, client_id: str, current_time: datetime) -> bool:
        """Check if client has exceeded rate limits."""
        minute_ago = current_time - timedelta(minutes=1)
        hour_ago = current_time - timedelta(hours=1)
        
        # Clean old requests
        minute_queue = self.minute_requests[client_id]
        hour_queue = self.hour_requests[client_id]
        
        # Remove requests older than 1 minute
        while minute_queue and minute_queue[0] < minute_ago:
            minute_queue.popleft()
        
        # Remove requests older than 1 hour
        while hour_queue and hour_queue[0] < hour_ago:
            hour_queue.popleft()
        
        # Check limits
        return (len(minute_queue) >= self.requests_per_minute or 
                len(hour_queue) >= self.requests_per_hour)

    def _record_request(self, client_id: str, current_time: datetime):
        """Record a request for rate limiting."""
        self.minute_requests[client_id].append(current_time)
        self.hour_requests[client_id].append(current_time)

    def _add_rate_limit_headers(self, response: Response, client_id: str, current_time: datetime):
        """Add rate limit headers to response."""
        minute_remaining = max(0, self.requests_per_minute - len(self.minute_requests[client_id]))
        hour_remaining = max(0, self.requests_per_hour - len(self.hour_requests[client_id]))
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking requests and adding correlation IDs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record request start time
        start_time = time.time()
        
        # Log request details
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent"),
                "content_length": request.headers.get("content-length")
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add tracking headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time, 3))
        
        # Log response details
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
                "response_size": response.headers.get("content-length")
            }
        )
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        
        except HTTPException:
            # Let HTTPExceptions pass through
            raise
        
        except Exception as exc:
            # Handle unexpected errors
            request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
            
            logger.error(
                "Unhandled exception in request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "exception": str(exc),
                    "exception_type": type(exc).__name__
                },
                exc_info=True
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={"X-Request-ID": request_id}
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response