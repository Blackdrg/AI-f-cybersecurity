"""
Service and model wrappers for external integrations.
"""
from typing import Any, Optional, Dict, List
import logging
import asyncio
from functools import wraps
import hashlib
import time
from collections import OrderedDict

from .adapters import BaseAdapter, AdapterConfig

logger = logging.getLogger(__name__)


def rate_limit(calls_per_second: float):
    """Rate limiting decorator."""
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                await asyncio.sleep(left_to_wait)
            last_called[0] = time.time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def circuit_breaker(func):
    """Circuit breaker decorator for adapter methods."""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if self._circuit_open:
            if self._last_failure_time and (time.time() - self._last_failure_time) > self.config.circuit_breaker_timeout:
                self._circuit_open = False
                self._failure_count = 0
            else:
                raise RuntimeError(f"Circuit breaker open for {self.config.name}")
        
        try:
            result = await func(self, *args, **kwargs)
            self._failure_count = 0
            self._circuit_open = False
            return result
        except Exception:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.config.circuit_breaker_threshold:
                self._circuit_open = True
                logger.warning(f"Circuit breaker opened for {self.config.name}")
            raise
    return wrapper


class ServiceWrapper(BaseAdapter):
    """Wrapper for external services with caching and rate limiting."""
    
    def __init__(self, config: AdapterConfig, client: Any = None):
        super().__init__(config)
        self.client = client
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _get_cache_key(self, data: Any) -> str:
        """Generate cache key from data."""
        if isinstance(data, dict):
            data = tuple(sorted(data.items()))
        return hashlib.md5(str(data).encode()).hexdigest()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            self._cache_hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        self._cache_misses += 1
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set value in cache."""
        self._cache[key] = value
        if len(self._cache) > 1000:
            self._cache.popitem(last=False)
    
    @rate_limit(calls_per_second=10.0)
    @circuit_breaker
    async def process(self, data: Any) -> Any:
        """Process through service with caching."""
        if not self.config.enabled:
            return None
        
        cache_key = self._get_cache_key(data)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = await self._execute(data)
        self._set_cache(cache_key, result)
        self._record_success()
        return result
    
    async def _execute(self, data: Any) -> Any:
        """Override this method for actual service calls."""
        raise NotImplementedError


class ModelWrapper(BaseAdapter):
    """Wrapper for ML models with preprocessing and postprocessing."""
    
    def __init__(self, config: AdapterConfig, model: Any = None):
        super().__init__(config)
        self.model = model
        self._preprocessors: List[Any] = []
        self._postprocessors: List[Any] = []
    
    def add_preprocessor(self, func):
        """Add preprocessing function."""
        self._preprocessors.append(func)
        return self
    
    def add_postprocessor(self, func):
        """Add postprocessing function."""
        self._postprocessors.append(func)
        return self
    
    async def process(self, data: Any) -> Any:
        """Process through model pipeline."""
        if not self.config.enabled or not self.model:
            return None
        
        for preproc in self._preprocessors:
            data = preproc(data)
        
        result = await self._infer(data)
        
        for postproc in self._postprocessors:
            result = postproc(result)
        
        self._record_success()
        return result
    
    async def _infer(self, data: Any) -> Any:
        """Run model inference."""
        return self.model(data)


class CacheWrapper(BaseAdapter):
    """Caching wrapper for any adapter."""
    
    def __init__(self, config: AdapterConfig, wrapped: BaseAdapter):
        super().__init__(config)
        self.wrapped = wrapped
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
    
    def _get_cache_key(self, data: Any) -> str:
        """Generate cache key."""
        if isinstance(data, dict):
            data = tuple(sorted(data.items()))
        return hashlib.md5(str(data).encode()).hexdigest()
    
    async def process(self, data: Any) -> Any:
        """Process with caching."""
        if not self.config.enabled:
            return await self.wrapped.process(data)
        
        key = self._get_cache_key(data)
        now = time.time()
        
        if key in self._cache and self._ttl.get(key, 0) > now:
            return self._cache[key]
        
        result = await self.wrapped.process(data)
        self._cache[key] = result
        self._ttl[key] = now + self.config.cache_ttl
        return result


class RateLimitWrapper(BaseAdapter):
    """Rate limiting wrapper."""
    
    def __init__(self, config: AdapterConfig, wrapped: BaseAdapter):
        super().__init__(config)
        self.wrapped = wrapped
        self._semaphore = asyncio.Semaphore(int(config.rate_limit_rps))
    
    async def process(self, data: Any) -> Any:
        """Process with rate limiting."""
        async with self._semaphore:
            return await self.wrapped.process(data)