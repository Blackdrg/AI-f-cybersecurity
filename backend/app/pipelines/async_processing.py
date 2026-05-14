"""
Async processing chains for concurrent operations.
"""
from typing import Any, Callable, List, Optional
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result from async processing."""
    success: bool
    data: Any = None
    error: Optional[Exception] = None


class AsyncChain:
    """Chain of async processors."""
    
    def __init__(self, name: str = "async_chain"):
        self.name = name
        self.processors: List[AsyncProcessor] = []
    
    def add_processor(self, name: str, func: Callable, parallel: bool = False) -> "AsyncChain":
        """Add a processor to the chain."""
        self.processors.append(AsyncProcessor(name, func, parallel))
        return self
    
    async def execute(self, data: Any = None) -> Any:
        """Execute all processors in chain."""
        result = data
        for processor in self.processors:
            out = processor.func(result)
            result = await out if asyncio.iscoroutine(out) else out
        return result


class AsyncProcessor:
    """Single async processor in a chain."""
    
    def __init__(self, name: str, func: Callable, parallel: bool = False):
        self.name = name
        self.func = func
        self.parallel = parallel
    
    async def execute(self, data: Any = None) -> Any:
        """Execute this processor."""
        try:
            out = self.func(data)
            return await out if asyncio.iscoroutine(out) else out
        except Exception as e:
            logger.error(f"Processor {self.name} failed: {e}")
            raise


class ProcessingChain:
    """Chain of processing steps with batching support."""
    
    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.steps: List[Callable] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    def add_step(self, func: Callable) -> "ProcessingChain":
        """Add processing step."""
        self.steps.append(func)
        return self
    
    async def process_batch(self, items: List[Any]) -> List[Any]:
        """Process items in batches."""
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = await self._process_batch(batch)
            results.extend(batch_results)
        return results
    
    async def _process_batch(self, batch: List[Any]) -> List[Any]:
        """Process a single batch."""
        async def process_with_semaphore(item):
            async with self._semaphore:
                result = item
                for step in self.steps:
                    out = step(result)
                    result = await out if asyncio.iscoroutine(out) else out
                return result
        
        tasks = [process_with_semaphore(item) for item in batch]
        return await asyncio.gather(*tasks, return_exceptions=True)