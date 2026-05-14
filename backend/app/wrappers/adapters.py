"""
Adapter abstraction layer for external services and models.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class AdapterConfig:
    """Configuration for adapter instances."""
    name: str
    enabled: bool = True
    timeout: float = 30.0
    retries: int = 3
    retry_backoff: float = 1.5
    cache_ttl: int = 300
    rate_limit_rps: float = 10.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    custom_config: Dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """Abstract base class for all adapters."""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self._circuit_open = False
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
    
    @abstractmethod
    async def process(self, data: Any) -> Any:
        """Process data through the adapter."""
        pass
    
    def _with_circuit_breaker(func):
        """Circuit breaker decorator for adapter methods."""
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if self._circuit_open:
                if self._last_failure_time and (time.time() - self._last_failure_time) > self.config.circuit_breaker_timeout:
                    self._circuit_open = False
                    self._failure_count = 0
                else:
                    raise RuntimeError(f"Circuit breaker open for {self.config.name}")
            
            return await func(self, *args, **kwargs)
        return wrapper
    
    def _record_failure(self):
        """Record adapter failure for circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.config.circuit_breaker_threshold:
            self._circuit_open = True
            logger.warning(f"Circuit breaker opened for {self.config.name}")
    
    def _record_success(self):
        """Record successful operation."""
        self._failure_count = 0
        self._circuit_open = False
    
    async def health_check(self) -> bool:
        """Check adapter health."""
        return True
    
    def close(self):
        """Cleanup resources."""
        pass


class AdapterRegistry:
    """Registry for managing adapter instances."""
    
    _adapters: Dict[str, BaseAdapter] = {}
    
    @classmethod
    def register(cls, name: str, adapter: BaseAdapter):
        """Register an adapter instance."""
        cls._adapters[name] = adapter
        logger.info(f"Registered adapter: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseAdapter]:
        """Get an adapter by name."""
        return cls._adapters.get(name)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """List all registered adapters."""
        return list(cls._adapters.keys())
    
    @classmethod
    def unregister(cls, name: str):
        """Unregister an adapter."""
        if name in cls._adapters:
            adapter = cls._adapters.pop(name)
            adapter.close()
            logger.info(f"Unregistered adapter: {name}")