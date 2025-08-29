"""
Abstract base service class for all services in the LOs Generation Pipeline.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import structlog
from src.core.config import get_settings


class BaseService(ABC):
    """Abstract base class for all services."""
    
    def __init__(self, name: str):
        """
        Initialize base service.
        
        Args:
            name: Service name for logging and identification
        """
        self.name = name
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__).bind(service=name)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize service resources."""
        if self._initialized:
            return
            
        self.logger.info("Initializing service", service_name=self.name)
        try:
            await self._initialize()
            self._initialized = True
            self.logger.info("Service initialized successfully", service_name=self.name)
        except Exception as e:
            self.logger.error(
                "Failed to initialize service", 
                service_name=self.name, 
                error=str(e)
            )
            raise
    
    async def shutdown(self) -> None:
        """Shutdown service resources."""
        if not self._initialized:
            return
            
        self.logger.info("Shutting down service", service_name=self.name)
        try:
            await self._shutdown()
            self._initialized = False
            self.logger.info("Service shutdown successfully", service_name=self.name)
        except Exception as e:
            self.logger.error(
                "Error during service shutdown", 
                service_name=self.name, 
                error=str(e)
            )
            raise
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Service-specific initialization logic."""
        pass
    
    @abstractmethod
    async def _shutdown(self) -> None:
        """Service-specific shutdown logic."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health status.
        
        Returns:
            Health status dictionary with service information
        """
        pass
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()