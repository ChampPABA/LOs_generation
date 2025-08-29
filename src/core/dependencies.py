"""
FastAPI dependency providers for the Learning Objectives Generation API.
Provides service instances, authentication, and common utilities.
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.services.processing_service import ProcessingService
from src.services.job_service import JobService
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Security
security = HTTPBearer()

# Service instances (singletons)
_processing_service: Optional[ProcessingService] = None
_job_service: Optional[JobService] = None

async def get_processing_service() -> ProcessingService:
    """
    Get or create the processing service instance.
    """
    global _processing_service
    
    if _processing_service is None:
        _processing_service = ProcessingService()
        await _processing_service.initialize()
        logger.info("Processing service initialized")
    
    return _processing_service

async def get_job_service() -> JobService:
    """
    Get or create the job service instance.
    """
    global _job_service
    
    if _job_service is None:
        _job_service = JobService()
        logger.info("Job service initialized")
    
    return _job_service

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Dict[str, Any]:
    """
    Get current authenticated user from token or API key.
    
    Args:
        credentials: Bearer token credentials
        x_api_key: Optional API key header
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Check API key first (simpler auth for development)
        if x_api_key:
            # In real implementation, this would validate against database
            if x_api_key == getattr(settings, 'api_key', 'development-key-12345'):
                return {
                    'user_id': 'api_user',
                    'username': 'API User',
                    'is_admin': True,
                    'auth_method': 'api_key'
                }
            else:
                logger.warning(f"Invalid API key attempted: {x_api_key[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
        
        # Check Bearer token
        if credentials:
            token = credentials.credentials
            
            # In real implementation, this would:
            # 1. Validate JWT token
            # 2. Check token expiration
            # 3. Extract user claims
            # 4. Verify user exists and is active
            
            # Mock token validation
            if token == "development-token-12345":
                return {
                    'user_id': 'dev_user_001',
                    'username': 'Developer',
                    'email': 'dev@example.com',
                    'is_admin': False,
                    'auth_method': 'bearer_token',
                    'permissions': ['read', 'write'],
                    'rate_limit_tier': 'standard'
                }
            else:
                logger.warning(f"Invalid bearer token attempted: {token[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        # No valid authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Ensure current user has admin privileges.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information if admin
        
    Raises:
        HTTPException: If user lacks admin privileges
    """
    if not current_user.get('is_admin', False):
        logger.warning(f"Non-admin user attempted admin action: {current_user.get('user_id')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    
    return current_user

def get_rate_limiter():
    """
    Get rate limiting dependency.
    
    Returns:
        Rate limiting function
    """
    # In real implementation, this would return a configured rate limiter
    # For now, return a no-op function
    async def no_op_limiter():
        pass
    
    return no_op_limiter

async def validate_content_type(content_type: str) -> str:
    """
    Validate content type parameter.
    
    Args:
        content_type: Content type to validate
        
    Returns:
        Validated content type
        
    Raises:
        HTTPException: If content type is invalid
    """
    valid_types = ["direct_text", "pdf_upload", "textbook_id"]
    
    if content_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content_type. Must be one of: {valid_types}"
        )
    
    return content_type

async def validate_processing_path(processing_path: Optional[str] = None) -> Optional[str]:
    """
    Validate processing path parameter.
    
    Args:
        processing_path: Processing path to validate
        
    Returns:
        Validated processing path
        
    Raises:
        HTTPException: If processing path is invalid
    """
    if processing_path is None:
        return None
    
    valid_paths = ["auto", "structural", "ocr_agentic"]
    
    if processing_path not in valid_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid processing_path. Must be one of: {valid_paths}"
        )
    
    return processing_path

class PaginationParams:
    """Pagination parameters for list endpoints."""
    
    def __init__(
        self,
        limit: int = 20,
        offset: int = 0,
        max_limit: int = 100
    ):
        self.limit = min(limit, max_limit)
        self.offset = max(offset, 0)
        self.max_limit = max_limit

def get_pagination_params(
    limit: int = 20,
    offset: int = 0
) -> PaginationParams:
    """
    Get pagination parameters with validation.
    
    Args:
        limit: Number of items to return
        offset: Number of items to skip
        
    Returns:
        Validated pagination parameters
    """
    return PaginationParams(limit=limit, offset=offset)

async def get_service_health() -> Dict[str, Any]:
    """
    Get overall service health status.
    
    Returns:
        Service health information
    """
    health_status = {
        'status': 'healthy',
        'services': {
            'processing_service': 'healthy',
            'database': 'healthy',  # Would check actual DB connection
            'redis': 'healthy',     # Would check actual Redis connection
            'storage': 'healthy'    # Would check file storage access
        },
        'timestamp': '2024-01-01T12:00:00Z'  # Would use actual timestamp
    }
    
    return health_status

# Cleanup function for application shutdown
async def cleanup_dependencies():
    """
    Cleanup function to properly shutdown services.
    """
    global _processing_service, _job_service
    
    if _processing_service:
        await _processing_service.shutdown()
        _processing_service = None
    
    if _job_service:
        _job_service = None
    
    logger.info("Dependencies cleaned up successfully")