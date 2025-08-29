"""
Circuit breaker implementation for external API resilience.
Protects against cascading failures and provides fallback mechanisms.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)

# Type variables for generic circuit breaker
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests rejected
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 60.0       # Seconds before trying again (open -> half-open)
    request_timeout: float = 30.0  # Individual request timeout
    failure_rate_threshold: float = 0.5  # Failure rate to trigger opening
    min_requests: int = 10      # Minimum requests before checking failure rate


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED
    state_changed_at: float = field(default_factory=time.time)
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=100))


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker(Generic[T]):
    """Circuit breaker for protecting external service calls."""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_func: Optional[Callable[..., Awaitable[T]]] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback_func = fallback_func
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized", extra={
            "failure_threshold": self.config.failure_threshold,
            "success_threshold": self.config.success_threshold,
            "timeout": self.config.timeout
        })
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            await self._update_state()
            
            if self.stats.current_state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker '{self.name}' is OPEN, rejecting request")
                if self.fallback_func:
                    logger.info(f"Using fallback for '{self.name}'")
                    return await self.fallback_func(*args, **kwargs)
                raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is open")
            
            # Track the request
            self.stats.total_requests += 1
        
        # Execute the function with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.request_timeout
            )
            await self._record_success()
            return result
            
        except Exception as e:
            await self._record_failure(e)
            raise
    
    async def _update_state(self):
        """Update circuit breaker state based on current conditions."""
        current_time = time.time()
        
        if self.stats.current_state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if current_time - self.stats.state_changed_at >= self.config.timeout:
                await self._transition_to_half_open()
        
        elif self.stats.current_state == CircuitState.CLOSED:
            # Check if we should open due to failures
            if await self._should_open():
                await self._transition_to_open()
        
        # Half-open state transitions are handled in record_success/failure
    
    async def _should_open(self) -> bool:
        """Determine if circuit should open based on failure rate."""
        if self.stats.total_requests < self.config.min_requests:
            return False
        
        # Check recent failure rate (last 100 requests)
        recent_total = len(self.stats.recent_failures) + len(self.stats.recent_successes)
        if recent_total < self.config.min_requests:
            return False
        
        failure_rate = len(self.stats.recent_failures) / recent_total
        return failure_rate >= self.config.failure_rate_threshold
    
    async def _record_success(self):
        """Record a successful request."""
        async with self._lock:
            self.stats.successful_requests += 1
            self.stats.last_success_time = time.time()
            self.stats.recent_successes.append(time.time())
            
            if self.stats.current_state == CircuitState.HALF_OPEN:
                # Check if we have enough successes to close
                recent_successes = sum(1 for t in self.stats.recent_successes 
                                     if time.time() - t < 60)  # Last minute
                
                if recent_successes >= self.config.success_threshold:
                    await self._transition_to_closed()
    
    async def _record_failure(self, exception: Exception):
        """Record a failed request."""
        async with self._lock:
            self.stats.failed_requests += 1
            self.stats.last_failure_time = time.time()
            self.stats.recent_failures.append(time.time())
            
            logger.warning(f"Circuit breaker '{self.name}' recorded failure", extra={
                "exception": str(exception),
                "failure_count": self.stats.failed_requests,
                "current_state": self.stats.current_state.value
            })
            
            if self.stats.current_state == CircuitState.HALF_OPEN:
                # Any failure in half-open state should open the circuit
                await self._transition_to_open()
            elif self.stats.current_state == CircuitState.CLOSED:
                # Check if we should open
                if await self._should_open():
                    await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transition to OPEN state."""
        self.stats.current_state = CircuitState.OPEN
        self.stats.state_changed_at = time.time()
        self.stats.circuit_opened_count += 1
        
        logger.error(f"Circuit breaker '{self.name}' OPENED", extra={
            "total_requests": self.stats.total_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": self._get_success_rate()
        })
    
    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.stats.current_state = CircuitState.HALF_OPEN
        self.stats.state_changed_at = time.time()
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
    
    async def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.stats.current_state = CircuitState.CLOSED
        self.stats.state_changed_at = time.time()
        
        logger.info(f"Circuit breaker '{self.name}' CLOSED (recovered)")
    
    def _get_success_rate(self) -> float:
        """Calculate current success rate."""
        if self.stats.total_requests == 0:
            return 1.0
        return self.stats.successful_requests / self.stats.total_requests
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.stats.current_state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": self._get_success_rate(),
            "circuit_opened_count": self.stats.circuit_opened_count,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "state_changed_at": self.stats.state_changed_at,
            "time_in_current_state": time.time() - self.stats.state_changed_at,
            "recent_failure_count": len(self.stats.recent_failures),
            "recent_success_count": len(self.stats.recent_successes)
        }
    
    async def reset(self):
        """Reset circuit breaker to closed state (for testing/manual recovery)."""
        async with self._lock:
            self.stats = CircuitBreakerStats()
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerRegistry:
    """Global registry for circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_func: Optional[Callable] = None
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config,
                    fallback_func=fallback_func
                )
            return self._breakers[name]
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        async with self._lock:
            return {name: breaker.get_stats() 
                   for name, breaker in self._breakers.items()}
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()


# Global registry instance
circuit_registry = CircuitBreakerRegistry()


# Decorator for easy circuit breaker usage
def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback_func: Optional[Callable] = None
):
    """Decorator to add circuit breaker protection to async functions."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            breaker = await circuit_registry.get_or_create(
                name=name,
                config=config,
                fallback_func=fallback_func
            )
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
