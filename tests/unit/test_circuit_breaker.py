"""
Unit tests for circuit breaker functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
import time

from src.api.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenException,
    CircuitBreakerRegistry,
    circuit_breaker,
    circuit_registry
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def config(self):
        """Test circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,  # Short timeout for testing
            request_timeout=0.5,
            failure_rate_threshold=0.5,
            min_requests=5
        )
    
    @pytest.fixture
    def circuit_breaker_instance(self, config):
        """Create circuit breaker instance for testing."""
        return CircuitBreaker("test_service", config)
    
    @pytest.fixture
    def slow_function(self):
        """Mock function that takes time to execute."""
        async def func():
            await asyncio.sleep(1.0)  # Longer than request timeout
            return "success"
        return func
    
    @pytest.fixture
    def failing_function(self):
        """Mock function that always fails."""
        async def func():
            raise Exception("Test failure")
        return func
    
    @pytest.fixture
    def successful_function(self):
        """Mock function that always succeeds."""
        async def func():
            return "success"
        return func
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self, circuit_breaker_instance):
        """Test circuit breaker initialization."""
        assert circuit_breaker_instance.name == "test_service"
        assert circuit_breaker_instance.stats.current_state == CircuitState.CLOSED
        assert circuit_breaker_instance.stats.total_requests == 0
        assert circuit_breaker_instance.stats.successful_requests == 0
        assert circuit_breaker_instance.stats.failed_requests == 0
    
    @pytest.mark.asyncio
    async def test_successful_request(self, circuit_breaker_instance, successful_function):
        """Test successful request handling."""
        result = await circuit_breaker_instance.call(successful_function)
        
        assert result == "success"
        assert circuit_breaker_instance.stats.total_requests == 1
        assert circuit_breaker_instance.stats.successful_requests == 1
        assert circuit_breaker_instance.stats.failed_requests == 0
        assert circuit_breaker_instance.stats.current_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_failed_request(self, circuit_breaker_instance, failing_function):
        """Test failed request handling."""
        with pytest.raises(Exception, match="Test failure"):
            await circuit_breaker_instance.call(failing_function)
        
        assert circuit_breaker_instance.stats.total_requests == 1
        assert circuit_breaker_instance.stats.successful_requests == 0
        assert circuit_breaker_instance.stats.failed_requests == 1
        assert circuit_breaker_instance.stats.current_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_timeout_request(self, circuit_breaker_instance, slow_function):
        """Test request timeout handling."""
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker_instance.call(slow_function)
        
        assert circuit_breaker_instance.stats.total_requests == 1
        assert circuit_breaker_instance.stats.successful_requests == 0
        assert circuit_breaker_instance.stats.failed_requests == 1
    
    @pytest.mark.asyncio
    async def test_circuit_opening_due_to_failures(self, circuit_breaker_instance, failing_function):
        """Test circuit opening due to consecutive failures."""
        # Generate enough failures to meet minimum request threshold
        for _ in range(5):
            with pytest.raises(Exception):
                await circuit_breaker_instance.call(failing_function)
        
        # Circuit should now be open
        assert circuit_breaker_instance.stats.current_state == CircuitState.OPEN
        assert circuit_breaker_instance.stats.failed_requests == 5
    
    @pytest.mark.asyncio
    async def test_circuit_rejection_when_open(self, circuit_breaker_instance, failing_function, successful_function):
        """Test request rejection when circuit is open."""
        # Open the circuit first
        for _ in range(5):
            with pytest.raises(Exception):
                await circuit_breaker_instance.call(failing_function)
        
        assert circuit_breaker_instance.stats.current_state == CircuitState.OPEN
        
        # Now try a request that would normally succeed
        with pytest.raises(CircuitBreakerOpenException):
            await circuit_breaker_instance.call(successful_function)
    
    @pytest.mark.asyncio
    async def test_fallback_function_when_open(self, config):
        """Test fallback function execution when circuit is open."""
        async def fallback_func():
            return "fallback_result"
        
        cb = CircuitBreaker("test_fallback", config, fallback_func)
        
        # Open the circuit
        async def failing_func():
            raise Exception("Test failure")
        
        for _ in range(5):
            with pytest.raises(Exception):
                await cb.call(failing_func)
        
        assert cb.stats.current_state == CircuitState.OPEN
        
        # Now call should use fallback
        result = await cb.call(lambda: "should_not_execute")
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_transition(self, circuit_breaker_instance, failing_function):
        """Test transition from open to half-open state."""
        # Open the circuit
        for _ in range(5):
            with pytest.raises(Exception):
                await circuit_breaker_instance.call(failing_function)
        
        assert circuit_breaker_instance.stats.current_state == CircuitState.OPEN
        
        # Wait for timeout to elapse
        await asyncio.sleep(1.1)  # Slightly longer than timeout
        
        # Next call should transition to half-open
        with pytest.raises(Exception):
            await circuit_breaker_instance.call(failing_function)
        
        # Should be open again after failure in half-open state
        assert circuit_breaker_instance.stats.current_state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_recovery(self, circuit_breaker_instance, failing_function, successful_function):
        """Test circuit recovery from open to closed state."""
        # Open the circuit
        for _ in range(5):
            with pytest.raises(Exception):
                await circuit_breaker_instance.call(failing_function)
        
        assert circuit_breaker_instance.stats.current_state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Make successful requests to recover
        for _ in range(2):  # success_threshold = 2
            result = await circuit_breaker_instance.call(successful_function)
            assert result == "success"
        
        # Circuit should now be closed
        assert circuit_breaker_instance.stats.current_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_get_stats(self, circuit_breaker_instance, successful_function):
        """Test circuit breaker statistics."""
        # Make some requests
        await circuit_breaker_instance.call(successful_function)
        await circuit_breaker_instance.call(successful_function)
        
        stats = circuit_breaker_instance.get_stats()
        
        assert stats["name"] == "test_service"
        assert stats["state"] == "closed"
        assert stats["total_requests"] == 2
        assert stats["successful_requests"] == 2
        assert stats["failed_requests"] == 0
        assert stats["success_rate"] == 1.0
        assert "last_success_time" in stats
        assert "state_changed_at" in stats
        assert "time_in_current_state" in stats
    
    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, circuit_breaker_instance, failing_function):
        """Test manual circuit breaker reset."""
        # Make some failures
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker_instance.call(failing_function)
        
        assert circuit_breaker_instance.stats.failed_requests == 3
        
        # Reset the circuit breaker
        await circuit_breaker_instance.reset()
        
        # Should be back to initial state
        assert circuit_breaker_instance.stats.current_state == CircuitState.CLOSED
        assert circuit_breaker_instance.stats.total_requests == 0
        assert circuit_breaker_instance.stats.successful_requests == 0
        assert circuit_breaker_instance.stats.failed_requests == 0


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functionality."""
    
    @pytest.mark.asyncio
    async def test_get_or_create_circuit_breaker(self):
        """Test getting or creating circuit breakers."""
        registry = CircuitBreakerRegistry()
        
        # Create new circuit breaker
        cb1 = await registry.get_or_create("service1")
        assert cb1.name == "service1"
        
        # Get existing circuit breaker
        cb2 = await registry.get_or_create("service1")
        assert cb1 is cb2  # Should be the same instance
        
        # Create different circuit breaker
        cb3 = await registry.get_or_create("service2")
        assert cb3.name == "service2"
        assert cb1 is not cb3
    
    @pytest.mark.asyncio
    async def test_get_all_stats(self):
        """Test getting all circuit breaker statistics."""
        registry = CircuitBreakerRegistry()
        
        # Create some circuit breakers
        cb1 = await registry.get_or_create("service1")
        cb2 = await registry.get_or_create("service2")
        
        # Get all stats
        all_stats = await registry.get_all_stats()
        
        assert "service1" in all_stats
        assert "service2" in all_stats
        assert all_stats["service1"]["name"] == "service1"
        assert all_stats["service2"]["name"] == "service2"
    
    @pytest.mark.asyncio
    async def test_reset_all_circuit_breakers(self):
        """Test resetting all circuit breakers."""
        registry = CircuitBreakerRegistry()
        
        # Create circuit breakers with some activity
        cb1 = await registry.get_or_create("service1")
        cb2 = await registry.get_or_create("service2")
        
        # Add some activity
        async def test_func():
            return "success"
        
        await cb1.call(test_func)
        await cb2.call(test_func)
        
        assert cb1.stats.total_requests == 1
        assert cb2.stats.total_requests == 1
        
        # Reset all
        await registry.reset_all()
        
        # All should be reset
        assert cb1.stats.total_requests == 0
        assert cb2.stats.total_requests == 0
    
    def test_global_registry_instance(self):
        """Test global circuit registry instance."""
        assert circuit_registry is not None
        assert isinstance(circuit_registry, CircuitBreakerRegistry)


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_decorator_basic_usage(self):
        """Test basic decorator usage."""
        @circuit_breaker(name="decorated_service")
        async def decorated_function():
            return "decorated_success"
        
        result = await decorated_function()
        assert result == "decorated_success"
        
        # Check that circuit breaker was created
        cb = await circuit_registry.get_or_create("decorated_service")
        assert cb.stats.total_requests == 1
        assert cb.stats.successful_requests == 1
    
    @pytest.mark.asyncio
    async def test_decorator_with_config(self):
        """Test decorator with custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            timeout=0.5
        )
        
        @circuit_breaker(name="configured_service", config=config)
        async def configured_function():
            return "configured_success"
        
        result = await configured_function()
        assert result == "configured_success"
        
        # Verify configuration was applied
        cb = await circuit_registry.get_or_create("configured_service")
        assert cb.config.failure_threshold == 2
        assert cb.config.success_threshold == 1
        assert cb.config.timeout == 0.5
    
    @pytest.mark.asyncio
    async def test_decorator_with_fallback(self):
        """Test decorator with fallback function."""
        async def fallback():
            return "fallback_result"
        
        @circuit_breaker(
            name="fallback_service",
            fallback_func=fallback
        )
        async def function_with_fallback():
            raise Exception("Always fails")
        
        # First few calls should fail normally
        for _ in range(5):
            with pytest.raises(Exception):
                await function_with_fallback()
        
        # After circuit opens, should use fallback
        result = await function_with_fallback()
        assert result == "fallback_result"


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout == 60.0
        assert config.request_timeout == 30.0
        assert config.failure_rate_threshold == 0.5
        assert config.min_requests == 10
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=30.0,
            request_timeout=10.0,
            failure_rate_threshold=0.3,
            min_requests=5
        )
        
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout == 30.0
        assert config.request_timeout == 10.0
        assert config.failure_rate_threshold == 0.3
        assert config.min_requests == 5
