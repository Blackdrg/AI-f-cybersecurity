"""
Incident Orchestration Engine
Full workflow automation with conditional branching, parallel execution, and escalation.
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict

from app.services.incident_response import IncidentResponseEngine, Incident
from app.services.connector_engine import ConnectorEvent, get_connector_registry

logger = logging.getLogger(__name__)


class IncidentStatus(str, Enum):
    NEW = "new"
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class IncidentSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def numeric(self):
        mapping = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
        return mapping.get(self.value, 0)


class WorkflowTrigger:
    """Defines a trigger condition that activates workflows."""

    def __init__(self, name, trigger_type, conditions, workflow_name, priority=5):
        self.name = name
        self.trigger_type = trigger_type
        self.conditions = conditions
        self.workflow_name = workflow_name
        self.priority = priority

    def matches(self, event):
        """Check if event matches this trigger."""
        for key, expected in self.conditions.items():
            actual = event.get(key)
            if actual is None:
                return False, 0.0

            if isinstance(expected, dict):
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

        confidence = self.conditions.get("confidence_boost", 1.0)
        return True, float(confidence)


@dataclass
class IncidentAction:
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

    async def execute(self, incident, engine):
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

            if condition and not self._evaluate_condition(condition, incident, engine):
                execution_log.append("SKIP '{}': condition not met".format(step_name))
                continue

            if requires_approval:
                approved = await self._request_approval(step_name, incident)
                if not approved:
                    execution_log.append("REJECTED '{}': approval denied".format(step_name))
                    if self.escalation:
                        await engine.escalate_incident(incident, self.escalation)
                    break

            action_result = {
                "step": step_name,
                "action": action,
                "started_at": datetime.utcnow().isoformat(),
                "params": params
            }

            try:
                from app.services.incident_response import IncidentActionExecutor
                executor = IncidentActionExecutor.get_instance()
                result = await asyncio.wait_for(
                    executor.execute(action, incident, params),
                    timeout=timeout
                )
                action_result["result"] = result
                action_result["status"] = "success"
                action_result["completed_at"] = datetime.utcnow().isoformat()
                execution_log.append("OK '{}': {}".format(step_name, result))
                if rollback:
                    rollback_stack.append((rollback, params, step_name))

            except asyncio.TimeoutError:
                action_result["status"] = "timeout"
                action_result["error"] = "Timed out after {}s".format(timeout)
                execution_log.append("TIMEOUT '{}': {}s".format(step_name, timeout))
                if rollback:
                    rollback_result = await self._execute_rollback(rollback, params, incident)
                    execution_log.append("ROLLBACK '{}' -> '{}': {}".format(step_name, rollback, rollback_result))

            except Exception as e:
                action_result["status"] = "failed"
                action_result["error"] = str(e)
                action_result["completed_at"] = datetime.utcnow().isoformat()
                execution_log.append("FAIL '{}': {}".format(step_name, e))
                if rollback:
                    rollback_result = await self._execute_rollback(rollback, params, incident)
                    execution_log.append("ROLLBACK '{}' -> '{}': {}".format(step_name, rollback, rollback_result))
                if step.get("on_failure") == "abort":
                    execution_log.append("ABORT: step '{}' failed with on_failure=abort".format(step_name))
                    break

            results.append(action_result)

        return {
            "playbook": self.name,
            "incident_id": incident.incident_id,
            "status": "completed",
            "steps_executed": len([r for r in results if r.get("status") == "success"]),
            "steps_failed": len([r for r in results if r.get("status") == "failed"]),
            "execution_log": execution_log,
            "rollback_applied": len(rollback_stack) > 0
        }

    def _evaluate_condition(self, condition, incident, engine):
        if "min_severity" in condition:
            sev_map = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
            if sev_map.get(incident.severity.value, 0) < sev_map.get(condition["min_severity"], 0):
                return False
        if "required_tags" in condition:
            tags = set(incident.tags) if hasattr(incident, 'tags') else set()
            if not condition["required_tags"].issubset(tags):
                return False
        if "threat_score_above" in condition:
            intel = incident.metadata.get("threat_intel", {})
            if intel.get("threat_score", 0) < condition["threat_score_above"]:
                return False
        return True

    async def _request_approval(self, step_name, incident):
        logger.info("Approval requested for step '{}' on incident {}".format(step_name, incident.incident_id))
        return True

    async def _execute_rollback(self, rollback_action, params, incident):
        from app.services.incident_response import IncidentActionExecutor
        executor = IncidentActionExecutor.get_instance()
        try:
            return await executor.execute(rollback_action, incident, params)
        except Exception as e:
            return "Rollback failed: {}".format(e)


class WorkflowManager:
    """Manages workflow triggers and conditional execution."""

    def __init__(self):
        self.triggers = []
        self.orchestrator = IncidentOrchestrator()
        self._setup_default_triggers()

    def _setup_default_triggers(self):
        self.triggers = [
            WorkflowTrigger(
                name="critical_threat_detected",
                trigger_type="event",
                conditions={"event_type": "threat_intel_match", "confidence": {"min": 0.7}, "severity": "critical"},
                workflow_name="critical_incident_response",
                priority=1
            ),
            WorkflowTrigger(
                name="high_confidence_threat",
                trigger_type="event",
                conditions={"event_type": "threat_intel_match", "threat_score": {"min": 70}},
                workflow_name="urgent_threat_response",
                priority=2
            ),
            WorkflowTrigger(
                name="brute_force_detection",
                trigger_type="event",
                conditions={"event_type": "login_failure", "count": {"min": 5}, "window_minutes": 5},
                workflow_name="brute_force_mitigation",
                priority=1
            ),
            WorkflowTrigger(
                name="spoofing_pattern",
                trigger_type="event",
                conditions={"event_type": "spoof_detection", "confidence": {"min": 0.8}},
                workflow_name="spoofing_response",
                priority=1
            ),
            WorkflowTrigger(
                name="data_exfiltration_suspect",
                trigger_type="event",
                conditions={"event_type": "anomaly", "anomaly_type": "data_volume", "threshold": {"min": 1000000}},
                workflow_name="data_leak_investigation",
                priority=2
            ),
            WorkflowTrigger(
                name="compliance_violation",
                trigger_type="event",
                conditions={"event_type": "compliance_breach", "regulation": {"in": ["GDPR", "CCPA", "SOC2"]}},
                workflow_name="compliance_incident_response",
                priority=1
            ),
            WorkflowTrigger(
                name="low_severity_log",
                trigger_type="event",
                conditions={"event_type": "threat_intel_match", "confidence": {"max": 0.3}, "severity": {"in": ["low", "info"]}},
                workflow_name="automated_log_only",
                priority=10
            ),
        ]

    def add_trigger(self, trigger):
        self.triggers.append(trigger)

    def remove_trigger(self, trigger_name):
        self.triggers = [t for t in self.triggers if t.name != trigger_name]

    def find_matching_triggers(self, event):
        matches = []
        for trigger in self.triggers:
            matched, confidence = trigger.matches(event)
            if matched:
                matches.append((trigger, confidence))
        matches.sort(key=lambda x: (x[0].priority, -x[1]))
        return [m[0] for m in matches]


class IncidentOrchestrator:
    """Full SOAR orchestration engine."""

    def __init__(self):
        self.workflow_manager = WorkflowManager()
        self.responder = IncidentResponseEngine.get_instance()
        self._active_incidents = {}

    async def process_event(self, event):
        matching_triggers = self.workflow_manager.find_matching_triggers(event)

        if not matching_triggers:
            logger.info("No workflow triggers matched for {} event".format(event.get("event_type", "unknown")))
            return {"action": "no_matching_workflow", "event_type": event.get("event_type")}

        results = []
        for trigger in matching_triggers[:3]:
            try:
                incident = await self._create_incident_from_trigger(trigger, event)
                self._active_incidents[incident.incident_id] = incident

                playbook = self.responder.playbooks.get(trigger.workflow_name)
                if playbook:
                    result = await playbook.execute(incident, self)
                else:
                    result = await self._execute_default_response(incident, trigger)

                result["incident_id"] = incident.incident_id
                result["trigger"] = trigger.name
                result["workflow"] = trigger.workflow_name
                results.append(result)

                await self._coordinate_external(incident, event)

            except Exception as e:
                logger.error("Workflow execution failed for {}: {}".format(trigger.name, e))
                results.append({"trigger": trigger.name, "error": str(e), "status": "failed"})

        return {
            "event_type": event.get("event_type"),
            "triggers_matched": len(matching_triggers),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def escalate_incident(self, incident, escalation_config):
        escalation_type = escalation_config.get("type", "none")
        target = escalation_config.get("target", "admin")

        if escalation_type == "pager":
            registry = get_connector_registry()
            pagerduty = registry.get("pagerduty")
            if pagerduty and pagerduty.status == "connected":
                event = {"event_type": "incident_escalation", "severity": incident.severity.value,
                         "incident_id": incident.incident_id, "description": incident.title}
                await pagerduty.send_event(event)

        elif escalation_type == "slack":
            registry = get_connector_registry()
            slack = registry.get("slack")
            if slack and slack.status == "connected":
                event = {"event_type": "incident_escalation",
                         "data": {"severity": incident.severity.value, "incident_id": incident.incident_id, "title": incident.title}}
                await slack.send_event(event)

        incident.status = IncidentStatus.ESCALATED.value

    async def _execute_default_response(self, incident, trigger):
        action_executor = IncidentResponseEngine.get_instance()._actions
        results = []
        for action_name in trigger.conditions.get("default_actions", ["alert_admin"]):
            action_cls = action_executor.get(action_name)
            if action_cls:
                try:
                    result = await action_cls.execute(action_name, incident, {})
                    results.append("{}: {}".format(action_name, result))
                except Exception as e:
                    results.append("{}: failed - {}".format(action_name, e))
        return {"playbook": "default", "steps_executed": len(results), "execution_log": results}

    async def _create_incident_from_trigger(self, trigger, event):
        incident_id = "INC-{}-{}".format(datetime.utcnow().strftime('%Y%m%d%H%M%S'), trigger.name[:8].upper())
        severity = IncidentSeverity.CRITICAL if trigger.priority <= 1 else \
                   IncidentSeverity.HIGH if trigger.priority <= 3 else \
                   IncidentSeverity.MEDIUM

        return Incident(
            incident_id=incident_id,
            title="{} - {}".format(trigger.name.replace('_', ' ').title(), event.get('event_type', 'unknown')),
            description="Triggered by {} matching event {}".format(trigger.name, event),
            severity=severity,
            status=IncidentStatus.OPEN,
            rules_matched=[trigger.name],
            metadata={"trigger": trigger.name, "trigger_conditions": trigger.conditions, "event": event}
        )

    async def _coordinate_external(self, incident, event):
        from app.services.connector_engine import ConnectorEvent, get_connector_registry
        registry = get_connector_registry()

        connector_event = ConnectorEvent(
            event_type=incident.title,
            data={"incident_id": incident.incident_id, "severity": incident.severity.value,
                  "description": incident.title, "recommended_actions": event.get("recommended_actions", []),
                  "threat_score": event.get("threat_assessment", {}).get("max_threat_score", 0)},
            metadata={"incident_id": incident.incident_id}
        )

        results = await registry.send_event_to_all(connector_event)

        siem_connectors = registry.get_by_type("siem")
        if siem_connectors:
            siem_event = ConnectorEvent(
                event_type="incident:{}".format(incident.severity.value),
                data={"incident_id": incident.incident_id, "severity": incident.severity.value,
                      "title": incident.title, "description": incident.description,
                      "ioc_data": event.get("threat_flags", [])},
                metadata={"incident_id": incident.incident_id}
            )
            for conn in siem_connectors:
                await conn.send_event(siem_event)

        for connector_name, result in results.items():
            incident.audit_log.append({"timestamp": datetime.utcnow().isoformat(),
                                       "action": "connector_notify:{}".format(connector_name),
                                       "result": str(result)})


# Global singleton
_orchestrated_manager = None


def get_orchestrated_manager():
    global _orchestrated_manager
    if _orchestrated_manager is None:
        _orchestrated_manager = OrchestratedResponseManager()
    return _orchestrated_manager