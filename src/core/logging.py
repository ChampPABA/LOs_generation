import structlog
import logging
import sys
from typing import Any, Dict
from .config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure structured logging."""
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LogContext:
    """Context manager for structured logging."""
    
    def __init__(self, **kwargs: Any):
        self.context = kwargs
        
    def __enter__(self) -> None:
        structlog.contextvars.bind_contextvars(**self.context)
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        for key in self.context:
            structlog.contextvars.unbind_contextvars(key)