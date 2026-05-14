"""
Enhanced SOAR Engine with Workflow Triggers and Incident Orchestration
"""
import os
import json
import logging
import asyncio
import httpx
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class IncidentStatus(str, Enum):
    """Incident lifecycle statuses."""
    NEW = "new"
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class IncidentSeverity(str, Enum):
    """Incident severity levels with numeric mapping."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def numeric(self) -> int:
        return {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}.get(self.value, 0)


class WorkflowTrigger:
    """Defines a trigger condition that activates workflows."""

    def __init__(self, name: str, trigger_type: str, conditions: Dict[str, Any],
                 workflow_name: str, priority: int = 5):
        self.name = name
        self.trigger_type = trigger_type  # event, timer, threshold, api_call
        self.conditions = conditions
        self.workflow_name = workflow_name
        self.priority = priority

    def matches(self, event: Dict[str, Any]) -> Tuple[bool, float]:
        """Check if event matches this trigger. Returns (matched, confidence)."""
        for key, expected in self.conditions.items():
            actual = event.get(key)
            if actual is None:
                return False, 0.0

            if isinstance(expected, dict):
                # Handle comparison operators
                if "min" in expected and actual < expected["min"]:
                    return False, 0.0
                if "max" in expected and actual > expected["max"]:
                    return False, 0.0
                if "equals" in expected and actual != expected["equals"]:
                    return False, 0.0
                if "in" in expected and actual not in expected["in"]:
                    return False, 0.0
                if "pattern" in expected:
                    import re
                    if not re.search(expected["pattern"], str(actual)):
                        return False, 0.0
            elif isinstance(expected, (int, float)):
                if actual < expected:
                    return False, 0.0
            elif actual != expected:
                return False, 0.0

        # Calculate match confidence
        confidence = self.conditions.get("confidence_boost", 1.0)
        return True, float(confidence)


@dataclass
class IncidentAction:
    """Represents a single remediation action in a playbook."""
    action_id: str
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 1
    rollback_action: str = ""
    enabled: bool = True
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class IncidentPlaybook:
    """Automated response playbook with conditional branching."""
    name: str
    description: str
    trigger_type: str = "event"
    priority: int = 5
    enabled: bool = True
    steps: List[Dict[str, Any]] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    escalation: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    async def execute(self, incident: "Incident", engine: "IncidentOrchestrator") -> Dict:
        """Execute playbook with conditional branching and rollback."""
        results = []
        execution_log = []
        rollback_stack = []

        for step in self.steps:
            step_name = step.get("step_name", step.get("action"))
            condition = step.get("condition")
            action = step.get("action")
            params = step.get("params", {})
            timeout = step.get("timeout_seconds", 300)
            requires_approval = step.get("requires_approval", False)
            rollback = step.get("rollback_action", "")

            # Check condition if present
            if condition and not self._evaluate_condition(condition, incident, engine):
                execution_log.append(f"SKIP '{step_name}': condition not met")
                continue

            # Check approval requirement
            if requires_approval:
                approved = await self._request_approval(step_name, incident)
                if not approved:
                    execution_log.append(f"REJECTED '{step_name}': approval denied")
                    # Execute escalation if configured
                    if self.escalation:
                        await engine.escalate_incident(incident, self.escalation)
                    break

            # Execute action with timeout
            action_result = {
                "step": step_name,
                "action": action,
                "started_at": datetime.utcnow().isoformat(),
                "params": params
            }

            try:
                from app.services.incident_response import IncidentActionExecutor
                executor = IncidentActionExecutor.get_instance()

                # Wrap in timeout
                result = await asyncio.wait_for(
                    executor.execute(action, incident, params),
                    timeout=timeout
                )

                action_result["result"] = result
                action_result["status"] = "success"
                action_result["completed_at"] = datetime.utcnow().isoformat()

                execution_log.append(f"OK '{step_name}': {result}")

                # Track for rollback
                if rollback:
                    rollback_stack.append((rollback, params, step_name))

            except asyncio.TimeoutError:
                action_result["status"] = "timeout"
                action_result["error"] = f"Timed out after {timeout}s"
                execution_log.append(f"TIMEOUT '{step_name}': {timeout}s")

                # Execute rollback for timed out action
                if rollback:
                    rollback_result = await self._execute_rollback(rollback, params, incident)
                    execution_log.append(f"ROLLBACK '{step_name}' → '{rollback}': {rollback_result}")

            except Exception as e:
                action_result["status"] = "failed"
                action_result["error"] = str(e)
                action_result["completed_at"] = datetime.utcnow().isoformat()
                execution_log.append(f"FAIL '{step_name}': {e}")

                # Execute rollback on failure
                if rollback:
                    rollback_result = await self._execute_rollback(rollback, params, incident)
                    execution_log.append(f"ROLLBACK '{step_name}' → '{rollback}': {rollback_result}")

                # Decide whether to continue or abort
                if step.get("on_failure") == "abort":
                    execution_log.append(f"ABORT: step '{step_name}' failed with on_failure=abort")
                    break

            results.append(action_result)

        return {
            "playbook": self.name,
            "incident_id": incident.incident_id,
            "status": "completed",
            "steps_executed": len([r for r in results if r.get("status") == "success"]),
            "steps_failed": len([r for r in results if r.get("status") == "failed"]),
            "steps_skipped": len([r for r in results if r.get("status") == "skipped"]),
            "execution_log": execution_log,
            "rollback_applied": len(rollback_stack) > 0
        }

    def _evaluate_condition(self, condition: Dict, incident: "Incident",
                            engine: "IncidentOrchestrator") -> bool:
        """Evaluate a step condition against current incident state."""
        if "min_severity" in condition:
            sev_map = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
            if sev_map.get(incident.severity.value, 0) < sev_map.get(condition["min_severity"], 0):
                return False

        if "required_tags" in condition:
            tags = set(incident.tags) if hasattr(incident, 'tags') else set()
            if not condition["required_tags"].issubset(tags):
                return False

        if "max_attempts" in condition:
            attempt_count = sum(1 for r in incident.audit_log if r.get("result", "").startswith("OK"))
            if attempt_count >= condition["max_attempts"]:
                return False

        if "threat_score_above" in condition:
            intel = incident.metadata.get("threat_intel", {})
            if intel.get("threat_score", 0) < condition["threat_score_above"]:
                return False

        return True

    async def _request_approval(self, step_name: str, incident: "Incident") -> bool:
        """Request approval for a critical action (simulated)."""
        logger.info(f"Approval requested for step '{step_name}' on incident {incident.incident_id}")
        # In production, this would integrate with approval workflows
        # For now, auto-approve non-destructive actions
        return True

    async def _execute_rollback(self, rollback_action: str, params: Dict, incident: "Incident") -> str:
        """Execute a rollback action."""
        from app.services.incident_response import IncidentActionExecutor
        executor = IncidentActionExecutor.get_instance()
        try:
            return await executor.execute(rollback_action, incident, params)
        except Exception as e:
            return f"Rollback failed: {e}"