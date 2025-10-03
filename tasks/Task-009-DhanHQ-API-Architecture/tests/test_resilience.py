"""
Unit tests for resilience utilities.
"""

import pytest
import time
from unittest.mock import Mock
from utils.resilience import (
    RetryStrategy,
    RateLimiter,
    CircuitBreaker,
    CircuitState
)


@pytest.mark.unit
class TestRetryStrategy:
    """Test RetryStrategy decorator."""
    
    def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        mock_func = Mock(return_value="success")
        
        @RetryStrategy(max_attempts=3)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_on_failure(self):
        """Test retries on failure."""
        mock_func = Mock(side_effect=[Exception("error"), Exception("error"), "success"])
        
        @RetryStrategy(max_attempts=3, backoff_factor=0.1)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test exception raised when max retries exceeded."""
        mock_func = Mock(side_effect=Exception("persistent error"))
        
        @RetryStrategy(max_attempts=3, backoff_factor=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(Exception, match="persistent error"):
            test_func()
        
        assert mock_func.call_count == 3


@pytest.mark.unit
class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_rate_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(rate=10, burst=10)
        
        # Should allow immediate calls up to burst
        for _ in range(10):
            assert limiter.acquire(blocking=False) is True
        
        # Next call should fail without blocking
        assert limiter.acquire(blocking=False) is False
    
    def test_token_refill(self):
        """Test tokens refill over time."""
        limiter = RateLimiter(rate=10, burst=5)
        
        # Use all tokens
        for _ in range(5):
            limiter.acquire()
        
        # Wait for tokens to refill
        time.sleep(0.6)  # 0.6s at 10/s = 6 tokens
        
        # Should have tokens again
        assert limiter.acquire(blocking=False) is True
    
    def test_decorator_usage(self):
        """Test RateLimiter as decorator."""
        limiter = RateLimiter(rate=100, burst=5)
        mock_func = Mock(return_value="success")
        
        @limiter
        def test_func():
            return mock_func()
        
        # Call up to burst
        for _ in range(5):
            result = test_func()
            assert result == "success"
        
        assert mock_func.call_count == 5


@pytest.mark.unit
class TestCircuitBreaker:
    """Test CircuitBreaker class."""
    
    def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=ValueError
        )
        
        mock_func = Mock(side_effect=ValueError("error"))
        
        @breaker
        def test_func():
            return mock_func()
        
        # Cause failures to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                test_func()
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Next call should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            test_func()
    
    def test_circuit_half_open_after_timeout(self):
        """Test circuit enters half-open after recovery timeout."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.5,
            expected_exception=ValueError
        )
        
        mock_func = Mock(side_effect=[
            ValueError("error"),
            ValueError("error"),
            "success"
        ])
        
        @breaker
        def test_func():
            return mock_func()
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                test_func()
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Wait for recovery
        time.sleep(0.6)
        
        # Should allow one call (half-open)
        result = test_func()
        assert result == "success"
    
    def test_circuit_closes_after_successes(self):
        """Test circuit closes after successful recovery."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.5,
            success_threshold=2,
            expected_exception=ValueError
        )
        
        mock_func = Mock(side_effect=[
            ValueError("error"),
            ValueError("error"),
            "success1",
            "success2"
        ])
        
        @breaker
        def test_func():
            return mock_func()
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                test_func()
        
        # Wait and recover
        time.sleep(0.6)
        
        # Two successful calls should close circuit
        test_func()
        test_func()
        
        assert breaker.get_state() == CircuitState.CLOSED
    
    def test_circuit_reset(self):
        """Test manual circuit reset."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=ValueError
        )
        
        mock_func = Mock(side_effect=ValueError("error"))
        
        @breaker
        def test_func():
            return mock_func()
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                test_func()
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Reset
        breaker.reset()
        
        assert breaker.get_state() == CircuitState.CLOSED

