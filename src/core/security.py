"""
Security utilities for API authentication, rate limiting, and security middleware.
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)
security = HTTPBearer()
settings = get_settings()


class APIKeyManager:
    """Manages API key generation, validation, and expiration."""
    
    def __init__(self):
        self.active_keys: Dict[str, Dict[str, Any]] = {}
        self.rate_limiters: Dict[str, Dict[str, Any]] = {}
    
    def generate_api_key(self, user_id: str = None, description: str = None) -> str:
        """
        Generate a new API key.
        
        Args:
            user_id: Optional user identifier
            description: Optional description for the key
            
        Returns:
            Generated API key string
        """
        # Generate secure random key
        key = f"los_{secrets.token_urlsafe(32)}"
        
        # Store key metadata
        self.active_keys[key] = {
            "user_id": user_id or "anonymous",
            "description": description or "Generated API key",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=settings.api_key_expiry_days),
            "last_used": None,
            "usage_count": 0,
            "is_active": True
        }
        
        # Initialize rate limiter for this key
        self.rate_limiters[key] = {
            "minute_requests": 0,
            "minute_reset": time.time() + 60,
            "hour_requests": 0,
            "hour_reset": time.time() + 3600
        }
        
        logger.info(
            "API key generated",
            key_prefix=key[:10] + "...",
            user_id=user_id,
            expires_at=self.active_keys[key]["expires_at"]
        )
        
        return key
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key and check expiration.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if key is valid and active
        """
        if not api_key or api_key not in self.active_keys:
            return False
        
        key_data = self.active_keys[api_key]
        
        # Check if key is active
        if not key_data.get("is_active", False):
            return False
        
        # Check expiration
        if datetime.utcnow() > key_data["expires_at"]:
            key_data["is_active"] = False
            logger.warning("API key expired", key_prefix=api_key[:10] + "...")
            return False
        
        # Update usage statistics
        key_data["last_used"] = datetime.utcnow()
        key_data["usage_count"] += 1
        
        return True
    
    def check_rate_limit(self, api_key: str) -> bool:
        """
        Check if API key has exceeded rate limits.
        
        Args:
            api_key: API key to check
            
        Returns:
            True if within rate limits
        """
        if api_key not in self.rate_limiters:
            return False
        
        limiter = self.rate_limiters[api_key]
        current_time = time.time()
        
        # Reset minute counter if needed
        if current_time > limiter["minute_reset"]:
            limiter["minute_requests"] = 0
            limiter["minute_reset"] = current_time + 60
        
        # Reset hour counter if needed
        if current_time > limiter["hour_reset"]:
            limiter["hour_requests"] = 0
            limiter["hour_reset"] = current_time + 3600
        
        # Check limits
        if limiter["minute_requests"] >= settings.api_rate_limit_per_minute:
            logger.warning(
                "API key exceeded minute rate limit",
                key_prefix=api_key[:10] + "...",
                requests=limiter["minute_requests"]
            )
            return False
        
        if limiter["hour_requests"] >= settings.api_rate_limit_per_hour:
            logger.warning(
                "API key exceeded hour rate limit",
                key_prefix=api_key[:10] + "...",
                requests=limiter["hour_requests"]
            )
            return False
        
        # Increment counters
        limiter["minute_requests"] += 1
        limiter["hour_requests"] += 1
        
        return True
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if key was revoked successfully
        """
        if api_key in self.active_keys:
            self.active_keys[api_key]["is_active"] = False
            logger.info("API key revoked", key_prefix=api_key[:10] + "...")
            return True
        return False
    
    def get_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get information about an API key."""
        if api_key in self.active_keys:
            key_data = self.active_keys[api_key].copy()
            # Don't expose sensitive data
            key_data.pop("user_id", None)
            return key_data
        return None


# Global API key manager instance
api_key_manager = APIKeyManager()


async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to validate API key from Authorization header.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Valid API key
        
    Raises:
        HTTPException: If key is invalid or rate limited
    """
    api_key = credentials.credentials
    
    # Validate API key
    if not api_key_manager.validate_api_key(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    
    # Check rate limits
    if not api_key_manager.check_rate_limit(api_key):
        raise HTTPException(
            status_code=429,
            detail="API rate limit exceeded"
        )
    
    return api_key


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    forwarded = request.headers.get("X-Forwarded")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data for logging/storage.
    
    Args:
        data: Sensitive data to hash
        
    Returns:
        SHA256 hash of the data
    """
    return hashlib.sha256(data.encode()).hexdigest()


def generate_request_id() -> str:
    """Generate unique request ID for tracing."""
    return secrets.token_hex(16)


class SecurityMiddleware:
    """Security middleware for request processing."""
    
    def __init__(self):
        self.blocked_ips: set = set()
        self.suspicious_requests: Dict[str, list] = {}
    
    def is_request_suspicious(self, request: Request) -> bool:
        """
        Check if request exhibits suspicious behavior.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if request is suspicious
        """
        client_ip = get_client_ip(request)
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return True
        
        # Check for common attack patterns in URL
        suspicious_patterns = [
            "../", "..\\", "<script", "SELECT ", "UNION ", "DROP ", 
            "INSERT ", "UPDATE ", "DELETE ", "exec(", "eval("
        ]
        
        url_path = str(request.url.path).lower()
        query_params = str(request.url.query).lower()
        
        for pattern in suspicious_patterns:
            if pattern.lower() in url_path or pattern.lower() in query_params:
                logger.warning(
                    "Suspicious request pattern detected",
                    client_ip=client_ip,
                    pattern=pattern,
                    path=url_path
                )
                return True
        
        return False
    
    def block_ip(self, ip: str, reason: str = "Security violation"):
        """
        Block an IP address.
        
        Args:
            ip: IP address to block
            reason: Reason for blocking
        """
        self.blocked_ips.add(ip)
        logger.warning("IP address blocked", ip=ip, reason=reason)
    
    def unblock_ip(self, ip: str):
        """
        Unblock an IP address.
        
        Args:
            ip: IP address to unblock
        """
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
            logger.info("IP address unblocked", ip=ip)


# Global security middleware instance
security_middleware = SecurityMiddleware()


def create_development_api_key() -> str:
    """Create a development API key for testing."""
    if settings.is_development:
        dev_key = api_key_manager.generate_api_key(
            user_id="dev_user",
            description="Development API key"
        )
        logger.info(
            "Development API key created",
            key=dev_key,
            note="Use this key for development and testing"
        )
        return dev_key
    else:
        raise ValueError("Development API keys can only be created in development mode")