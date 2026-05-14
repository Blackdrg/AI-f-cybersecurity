"""
Pipeline orchestrator for managing execution flow.
"""
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    stage: str
    data: Any = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PipelineOrchestrator:
    """Orchestrates multi-stage pipeline execution."""
    
    def __init__(self, name: str):
        self.name = name
        self._stages: List[Callable] = []
        self._stage_names: List[str] = []
        self._results: List[PipelineResult] = []
    
    def add_stage(self, name: str, func: Callable) -> "PipelineOrchestrator":
        """Add a processing stage."""
        self._stages.append(func)
        self._stage_names.append(name)
        return self
    
    def add_conditional_stage(self, name: str, condition: Callable, func: Callable) -> "PipelineOrchestrator":
        """Add a stage that runs only if condition is met."""
        async def conditional_wrapper(data):
            if await condition(data):
                return await func(data)
            return data
        return self.add_stage(name, conditional_wrapper)
    
    async def execute(self, initial_data: Any = None) -> PipelineResult:
        """Execute all stages in sequence."""
        self._results = []
        data = initial_data
        
        for stage_name, stage_func in zip(self._stage_names, self._stages):
            try:
                stage_result = stage_func(data)
                result_data = await stage_result if asyncio.iscoroutine(stage_result) else stage_result
                result = PipelineResult(
                    success=True,
                    stage=stage_name,
                    data=result_data
                )
                data = result.data
                self._results.append(result)
            except Exception as e:
                result = PipelineResult(
                    success=False,
                    stage=stage_name,
                    data=data,
                    error=e
                )
                self._results.append(result)
                if "failed" not in self.name.lower():
                    break
        
        return self._results[-1] if self._results else PipelineResult(
            success=True,
            stage="none",
            data=initial_data
        )
    
    def get_results(self) -> List[PipelineResult]:
        """Get all stage results."""
        return self._results
    
    def reset(self):
        """Reset pipeline state."""
        self._results = []