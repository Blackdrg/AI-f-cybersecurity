"""
AI workflow pipeline for complex AI operations.
"""
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """Single step in an AI workflow."""
    name: str
    execute: Callable
    condition: Optional[Callable] = None
    rollback: Optional[Callable] = None
    timeout: float = 60.0
    required: bool = True


class AIWorkflow:
    """Manages complex AI workflows with branching and rollback."""
    
    def __init__(self, name: str):
        self.name = name
        self.steps: List[WorkflowStep] = []
        self.state = WorkflowState.PENDING
        self._context: Dict[str, Any] = {}
        self._executed_steps: List[str] = []
    
    def add_step(self, step: WorkflowStep) -> "AIWorkflow":
        """Add a workflow step."""
        self.steps.append(step)
        return self
    
    async def execute(self, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute all workflow steps."""
        self._context = initial_context or {}
        self.state = WorkflowState.RUNNING
        self._executed_steps = []
        
        try:
            for step in self.steps:
                if step.condition and not await step.condition(self._context):
                    continue
                
                try:
                    result = step.execute(self._context)
                    self._context = await result if asyncio.iscoroutine(result) else result
                    self._executed_steps.append(step.name)
                except asyncio.TimeoutError:
                    logger.error(f"Step {step.name} timed out")
                    if step.required:
                        raise
                except Exception as e:
                    logger.error(f"Step {step.name} failed: {e}")
                    if step.required and step.rollback:
                        await step.rollback(self._context)
                    elif step.required:
                        self.state = WorkflowState.FAILED
                        raise
            
            self.state = WorkflowState.COMPLETED
            return self._context
        except Exception as e:
            self.state = WorkflowState.FAILED
            raise
    
    def pause(self):
        """Pause workflow execution."""
        self.state = WorkflowState.PAUSED
    
    def resume(self):
        """Resume paused workflow."""
        if self.state == WorkflowState.PAUSED:
            self.state = WorkflowState.RUNNING
    
    def get_executed_steps(self) -> List[str]:
        """Get list of executed step names."""
        return self._executed_steps.copy()