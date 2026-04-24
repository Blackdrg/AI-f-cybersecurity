import asyncio
import time
import functools
import logging
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """
    Circuit Breaker pattern to prevent cascading failures.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit Breaker HALF_OPEN")
                else:
                    raise CircuitBreakerOpenException(f"Circuit is OPEN for {func.__name__}")

            try:
                result = await func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failures = 0
                    logger.info("Circuit Breaker CLOSED")
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.error(f"Circuit Breaker OPEN for {func.__name__} due to: {e}")
                raise e
        return wrapper

def retry_with_backoff(retries: int = 3, backoff_in_seconds: int = 1, exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Decorator for retrying a function with exponential backoff.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if x == retries:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise e
                    sleep_time = (backoff_in_seconds * 2 ** x)
                    logger.warning(f"Retry {x+1}/{retries} for {func.__name__} after {sleep_time}s")
                    await asyncio.sleep(sleep_time)
                    x += 1
        return wrapper
    return decorator

# Shared circuit breakers for critical services
db_circuit_breaker = CircuitBreaker(failure_threshold=10, recovery_timeout=60)
redis_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
ai_model_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
