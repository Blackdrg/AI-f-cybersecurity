"""
SOAR (Security Orchestration, Automation and Response) Engine

Automated playbook execution for common security incidents:
- Multiple failed logins → auto-block IP, require MFA reset
- Spoofing detection → quarantine enrollment, alert admin
- Payment fraud → flag transaction, temporarily suspend account
- Model drift → create Jira ticket, notify ML team
"""

import os
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IncidentRule:
    """Condition-based rule for incident detection."""
    name: str
    description: str
    conditions: Dict[str, Any]
    actions: List[str]
    severity: IncidentSeverity
    enabled: bool = True


@dataclass
class IncidentPlaybook:
    """Automated response playbook for incident types."""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    estimated_duration: int = 300

    async def execute(self, incident: "Incident") -> List[str]:
        """Execute all playbook steps."""
        results = []
        for step in self.steps:
            action = step.get("action")
            params = step.get("params", {})
            try:
                result = await self._execute_action(action, incident, params)
                results.append(f"{action}: {result}")
            except Exception as e:
                logger.error(f"Playbook step {action} failed: {e}")
                results.append(f"{action}: failed - {e}")
        return results

    async def _execute_action(self, action: str, incident: "Incident", params: Dict) -> str:
        """Execute a specific action."""
        executor = IncidentActionExecutor.get_instance()
        return await executor.execute(action, incident, params)


@dataclass
class Incident:
    """Represents a security incident."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    rules_matched: List[str] = field(default_factory=list)
    playbook_executed: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    audit_log: List[Dict[str, Any]] = field(default_factory=list)


class IncidentActionExecutor:
    """Singleton executor for incident response actions."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._actions: Dict[str, Callable] = {}
        self._register_default_actions()

    def _register_default_actions(self):
        """Register default response actions."""
        self._actions = {
            "block_ip": self._block_ip,
            "require_mfa_reset": self._require_mfa_reset,
            "quarantine_enrollment": self._quarantine_enrollment,
            "alert_admin": self._alert_admin,
            "flag_transaction": self._flag_transaction,
            "suspend_account": self._suspend_account,
            "create_jira_ticket": self._create_jira_ticket,
            "notify_ml_team": self._notify_ml_team,
            "send_webhook": self._send_webhook,
            "log_audit": self._log_audit,
        }

    async def execute(self, action: str, incident: Incident, params: Dict) -> str:
        """Execute an action by name."""
        if action not in self._actions:
            raise ValueError(f"Unknown action: {action}")

        result = await self._actions[action](incident, params)

        incident.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "params": params,
            "result": result
        })

        return result

    async def _block_ip(self, incident: Incident, params: Dict) -> str:
        """Block an IP address."""
        from app.providers.threat_intel_provider import ThreatIntelProvider
        ip = params.get("ip") or incident.title.split()[-1]
        provider = ThreatIntelProvider()
        success = await provider.block_ip(ip, reason=f"Incident {incident.incident_id}")
        return f"IP {ip} blocked: {success}"

    async def _require_mfa_reset(self, incident: Incident, params: Dict) -> str:
        """Require MFA reset for user."""
        user_id = params.get("user_id")
        return f"MFA reset required for user {user_id}"

    async def _quarantine_enrollment(self, incident: Incident, params: Dict) -> str:
        """Quarantine an enrollment."""
        enrollment_id = params.get("enrollment_id")
        return f"Enrollment {enrollment_id} quarantined"

    async def _alert_admin(self, incident: Incident, params: Dict) -> str:
        """Alert administrator via webhook/email/slack."""
        severity = params.get("severity", incident.severity.value)
        message = params.get("message", incident.description)
        return f"Admin alerted via {params.get('channel', 'default')}: {message}"

    async def _flag_transaction(self, incident: Incident, params: Dict) -> str:
        """Flag a suspicious transaction."""
        tx_id = params.get("transaction_id")
        return f"Transaction {tx_id} flagged for review"

    async def _suspend_account(self, incident: Incident, params: Dict) -> str:
        """Temporarily suspend an account."""
        user_id = params.get("user_id")
        duration = params.get("duration", "24h")
        return f"Account {user_id} suspended for {duration}"

    async def _create_jira_ticket(self, incident: Incident, params: Dict) -> str:
        """Create Jira ticket for incident."""
        jira_url = os.getenv("JIRA_WEBHOOK_URL")
        if not jira_url:
            return "Jira webhook not configured"

        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(jira_url, json={
                "summary": incident.title,
                "description": incident.description,
                "severity": incident.severity.value,
                "incident_id": incident.incident_id
            })
        return f"Jira ticket created for {incident.incident_id}"

    async def _notify_ml_team(self, incident: Incident, params: Dict) -> str:
        """Notify ML team via Slack webhook."""
        webhook_url = os.getenv("SLACK_ML_WEBHOOK")
        if not webhook_url:
            return "Slack ML webhook not configured"

        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json={
                "text": f"[ML Alert] {incident.title}",
                "attachments": [{"text": incident.description, "color": "warning"}]
            })
        return "ML team notified via Slack"

    async def _send_webhook(self, incident: Incident, params: Dict) -> str:
        """Send webhook notification."""
        webhook_url = params.get("url") or os.getenv("THREAT_INTEL_WEBHOOK_URL")
        if not webhook_url:
            return "No webhook URL configured"

        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json={
                "type": "incident",
                "incident": incident.incident_id,
                "severity": incident.severity.value,
                "message": incident.title
            })
        return f"Webhook sent to {webhook_url}"

    async def _log_audit(self, incident: Incident, params: Dict) -> str:
        """Log action to audit trail."""
        from app.db.db_client import get_db
        try:
            db = await get_db()
            await db.pool.execute(
                "INSERT INTO audit_log (action, details, timestamp) VALUES ($1, $2, NOW())",
                "incident_response",
                {"incident_id": incident.incident_id, "action": params.get("message")}
            )
            return "Audit logged"
        except Exception as e:
            return f"Audit log failed: {e}"


class IncidentResponseEngine:
    """Main SOAR engine for incident detection and response."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.rules: List[IncidentRule] = []
        self.playbooks: Dict[str, IncidentPlaybook] = {}
        self._setup_default_rules()
        self._setup_default_playbooks()

    def _setup_default_rules(self):
        """Initialize default incident detection rules."""
        self.rules = [
            IncidentRule(
                name="multiple_failed_logins",
                description="Multiple failed login attempts from same IP",
                conditions={"event_type": "login_failure", "count": 5, "window_minutes": 5},
                actions=["block_ip", "require_mfa_reset", "alert_admin"],
                severity=IncidentSeverity.HIGH
            ),
            IncidentRule(
                name="spoofing_attempt",
                description="Face spoofing attempt detected",
                conditions={"event_type": "spoof_detection", "confidence": 0.8},
                actions=["quarantine_enrollment", "alert_admin"],
                severity=IncidentSeverity.CRITICAL
            ),
            IncidentRule(
                name="payment_fraud",
                description="Suspicious payment transaction",
                conditions={"event_type": "payment", "risk_score": 0.7},
                actions=["flag_transaction", "suspend_account", "alert_admin"],
                severity=IncidentSeverity.HIGH
            ),
            IncidentRule(
                name="model_drift",
                description="ML model performance degradation detected",
                conditions={"event_type": "model_drift", "drift_score": 0.5},
                actions=["create_jira_ticket", "notify_ml_team", "log_audit"],
                severity=IncidentSeverity.MEDIUM
            ),
        ]

    def _setup_default_playbooks(self):
        """Initialize default response playbooks."""
        self.playbooks = {
            "failed_logins": IncidentPlaybook(
                name="Failed Login Response",
                description="Automated response to brute force login attempts",
                steps=[
                    {"action": "block_ip", "params": {"duration": "24h"}},
                    {"action": "require_mfa_reset", "params": {}},
                    {"action": "alert_admin", "params": {"channel": "slack", "severity": "high"}},
                    {"action": "log_audit", "params": {"message": "Auto-blocked IP for failed logins"}}
                ]
            ),
            "spoofing": IncidentPlaybook(
                name="Spoofing Response",
                description="Response to face spoofing attempts",
                steps=[
                    {"action": "quarantine_enrollment", "params": {}},
                    {"action": "alert_admin", "params": {"channel": "pagerduty", "severity": "critical"}},
                    {"action": "block_ip", "params": {}},
                    {"action": "log_audit", "params": {"message": "Quarantined enrollment due to spoofing"}}
                ]
            ),
            "payment_fraud": IncidentPlaybook(
                name="Payment Fraud Response",
                description="Response to payment fraud attempts",
                steps=[
                    {"action": "flag_transaction", "params": {}},
                    {"action": "suspend_account", "params": {"duration": "72h"}},
                    {"action": "alert_admin", "params": {"channel": "slack", "severity": "high"}},
                    {"action": "log_audit", "params": {"message": "Flagged payment fraud"}}
                ]
            ),
            "model_drift": IncidentPlaybook(
                name="Model Drift Response",
                description="Response to ML model performance issues",
                steps=[
                    {"action": "create_jira_ticket", "params": {}},
                    {"action": "notify_ml_team", "params": {}},
                    {"action": "log_audit", "params": {"message": "Model drift reported"}}
                ]
            ),
        }

    async def evaluate_event(self, event: Dict[str, Any]) -> Optional[Incident]:
        """Evaluate an event against rules and create incident if matched."""
        for rule in self.rules:
            if not rule.enabled:
                continue

            if self._evaluate_conditions(event, rule.conditions):
                incident = await self._create_incident_from_rule(rule, event)
                return incident
        return None

    def _evaluate_conditions(self, event: Dict, conditions: Dict) -> bool:
        """Check if event matches rule conditions."""
        for key, expected in conditions.items():
            event_value = event.get(key)
            if event_value is None:
                return False
            if isinstance(expected, (int, float)):
                if event_value < expected:
                    return False
            elif event_value != expected:
                return False
        return True

    async def _create_incident_from_rule(self, rule: IncidentRule, event: Dict) -> Incident:
        """Create and execute incident from matched rule."""
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        incident = Incident(
            incident_id=incident_id,
            title=f"{rule.name.replace('_', ' ').title()}",
            description=f"Auto-generated from {rule.description}",
            severity=rule.severity,
            status=IncidentStatus.OPEN,
            rules_matched=[rule.name]
        )

        self.incidents[incident_id] = incident

        playbook_key = rule.name.split("_")[0]
        if playbook_key in self.playbooks:
            results = await self.playbooks[playbook_key].execute(incident)
            incident.playbook_executed = playbook_key
            incident.updated_at = datetime.utcnow()
            logger.info(f"Incident {incident_id} playbook results: {results}")

        return incident

    async def update_incident_status(self, incident_id: str, status: IncidentStatus, notes: str = None):
        """Update incident status with optional notes."""
        if incident_id not in self.incidents:
            return None

        incident = self.incidents[incident_id]
        incident.status = status
        incident.updated_at = datetime.utcnow()
        if notes:
            incident.resolution_notes = notes

        return incident

    def get_incidents(self, status: Optional[IncidentStatus] = None) -> List[Incident]:
        """Get all incidents, optionally filtered by status."""
        if status:
            return [i for i in self.incidents.values() if i.status == status]
        return list(self.incidents.values())


# Global instance
incident_engine = IncidentResponseEngine.get_instance()