"""
Resilience utilities for DhanHQ API calls.

Provides retry logic, rate limiting, and circuit breaking for robust API interactions.
"""

import logging
import time
import threading
from typing import Callable, Any, Optional
from functools import wraps
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, rejecting requests
    HALF_OPEN = "half_open"  # Testing if circuit can close


class RetryStrategy:
    """
    Retry strategy with exponential backoff.
    
    Usage:
        @RetryStrategy(max_attempts=3, backoff_factor=2.0)
        def api_call():
            return client.get_data()
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        max_backoff: float = 30.0,
        exceptions: tuple = (Exception,),
        on_retry: Optional[Callable] = None
    ):
        """
        Initialize retry strategy.
        
        Args:
            max_attempts: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            max_backoff: Maximum backoff time in seconds
            exceptions: Tuple of exceptions to catch and retry
            on_retry: Optional callback function called on each retry
        """
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.exceptions = exceptions
        self.on_retry = on_retry
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply retry logic."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e
                    
                    if attempt == self.max_attempts:
                        logger.error(
                            f"Max retry attempts ({self.max_attempts}) reached for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": attempt,
                                "error": str(e)
                            }
                        )
                        raise
                    
                    # Calculate backoff
                    backoff = min(
                        self.backoff_factor ** (attempt - 1),
                        self.max_backoff
                    )
                    
                    # Add jitter (±25%)
                    import random
                    jitter = backoff * random.uniform(0.75, 1.25)
                    
                    logger.warning(
                        f"Retry attempt {attempt}/{self.max_attempts} for {func.__name__} "
                        f"after {jitter:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "backoff": jitter,
                            "error": str(e)
                        }
                    )
                    
                    # Call retry callback if provided
                    if self.on_retry:
                        self.on_retry(attempt, e)
                    
                    time.sleep(jitter)
            
            # This should never be reached due to raise in loop
            raise last_exception
        
        return wrapper


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Usage:
        limiter = RateLimiter(rate=10, burst=20)
        
        @limiter
        def api_call():
            return client.get_data()
    """
    
    def __init__(self, rate: float, burst: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            rate: Requests per second
            burst: Burst capacity (defaults to rate if not provided)
        """
        self.rate = rate
        self.burst = burst if burst is not None else int(rate)
        self.tokens = self.burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.burst, self.tokens + tokens_to_add)
        self.last_update = now
    
    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            blocking: If True, wait until tokens available. If False, return immediately.
        
        Returns:
            True if tokens acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if not blocking:
                return False
            
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.rate
            
            logger.debug(
                f"Rate limit reached, waiting {wait_time:.2f}s",
                extra={
                    "tokens_available": self.tokens,
                    "tokens_needed": tokens,
                    "wait_time": wait_time
                }
            )
        
        # Wait outside the lock
        time.sleep(wait_time)
        
        # Try again after waiting
        with self.lock:
            self._refill_tokens()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Should not happen, but handle gracefully
            return False
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.acquire()
            return func(*args, **kwargs)
        
        return wrapper


class CircuitBreaker:
    """
    Circuit breaker pattern for API calls.
    
    Prevents cascading failures by temporarily stopping calls to failing services.
    
    Usage:
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=requests.exceptions.RequestException
        )
        
        @breaker
        def api_call():
            return client.get_data()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers the circuit
            success_threshold: Successful calls needed to close circuit from half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()
    
    def _record_success(self):
        """Record a successful call."""
        with self.lock:
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                
                if self.success_count >= self.success_threshold:
                    logger.info("Circuit breaker closing after successful recovery")
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
    
    def _record_failure(self):
        """Record a failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.success_count = 0
            
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker opening after {self.failure_count} failures",
                    extra={
                        "failure_count": self.failure_count,
                        "threshold": self.failure_threshold
                    }
                )
                self.state = CircuitState.OPEN
    
    def _can_attempt(self) -> bool:
        """Check if a call attempt is allowed."""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if (time.time() - self.last_failure_time) >= self.recovery_timeout:
                    logger.info("Circuit breaker entering half-open state for recovery test")
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                    self.success_count = 0
                    return True
                
                return False
            
            # HALF_OPEN state
            return True
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self._can_attempt():
                raise Exception(
                    f"Circuit breaker is OPEN for {func.__name__}. "
                    f"Retry after {self.recovery_timeout}s"
                )
            
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            
            except self.expected_exception as e:
                self._record_failure()
                raise
        
        return wrapper
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state
    
    def reset(self):
        """Manually reset the circuit breaker."""
        with self.lock:
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker manually reset")


# Convenience function to combine all resilience features
def resilient_api_call(
    func: Callable,
    max_retries: int = 3,
    rate_limit: Optional[float] = None,
    circuit_breaker: Optional[CircuitBreaker] = None
) -> Any:
    """
    Execute API call with retry, rate limiting, and circuit breaking.
    
    Args:
        func: Function to call
        max_retries: Maximum retry attempts
        rate_limit: Requests per second limit (None = no limit)
        circuit_breaker: CircuitBreaker instance (None = no circuit breaker)
    
    Returns:
        Result of function call
    """
    # Apply decorators in order: circuit breaker -> rate limiter -> retry
    decorated_func = func
    
    if max_retries > 1:
        retry_decorator = RetryStrategy(max_attempts=max_retries)
        decorated_func = retry_decorator(decorated_func)
    
    if rate_limit is not None:
        rate_limiter = RateLimiter(rate=rate_limit)
        decorated_func = rate_limiter(decorated_func)
    
    if circuit_breaker is not None:
        decorated_func = circuit_breaker(decorated_func)
    
    return decorated_func()

