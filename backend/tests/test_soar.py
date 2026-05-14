import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.incident_response import (
    IncidentStatus, IncidentSeverity, IncidentRule, IncidentPlaybook,
    Incident, IncidentActionExecutor, IncidentResponseEngine, incident_engine
)


class TestIncidentEnums:
    def test_incident_status_values(self):
        assert IncidentStatus.OPEN.value == "open"
        assert IncidentStatus.INVESTIGATING.value == "investigating"
        assert IncidentStatus.CONTAINED.value == "contained"
        assert IncidentStatus.RESOLVED.value == "resolved"
        assert IncidentStatus.CLOSED.value == "closed"

    def test_incident_severity_values(self):
        assert IncidentSeverity.LOW.value == "low"
        assert IncidentSeverity.MEDIUM.value == "medium"
        assert IncidentSeverity.HIGH.value == "high"
        assert IncidentSeverity.CRITICAL.value == "critical"


class TestIncidentRule:
    def test_rule_creation(self):
        rule = IncidentRule(
            name="test_rule",
            description="Test rule",
            conditions={"event_type": "test"},
            actions=["alert_admin"],
            severity=IncidentSeverity.HIGH
        )
        assert rule.name == "test_rule"
        assert rule.enabled is True


class TestIncident:
    def test_incident_creation(self):
        incident = Incident(
            incident_id="INC-20240101000000",
            title="Test Incident",
            description="Test description",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN
        )
        assert incident.incident_id == "INC-20240101000000"
        assert incident.created_at is not None


class TestIncidentActionExecutor:
    def test_singleton(self):
        e1 = IncidentActionExecutor.get_instance()
        e2 = IncidentActionExecutor.get_instance()
        assert e1 is e2

    @pytest.mark.asyncio
    async def test_block_ip(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test IP blocked 1.2.3.4",
            description="Test",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN
        )

        with patch("app.providers.threat_intel_provider.ThreatIntelProvider.block_ip", new_callable=AsyncMock) as mock_block:
            mock_block.return_value = True

            from app.services.incident_response import IncidentActionExecutor as Executor
            executor = Executor()
            result = await executor._block_ip(incident, {"ip": "1.2.3.4"})
            assert "blocked" in result.lower()

    @pytest.mark.asyncio
    async def test_require_mfa_reset(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN
        )
        result = await executor._require_mfa_reset(incident, {"user_id": "user123"})
        assert "MFA reset" in result

    @pytest.mark.asyncio
    async def test_quarantine_enrollment(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN
        )
        result = await executor._quarantine_enrollment(incident, {"enrollment_id": "enr123"})
        assert "quarantined" in result

    @pytest.mark.asyncio
    async def test_alert_admin(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test alert",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN
        )
        result = await executor._alert_admin(incident, {"channel": "slack", "severity": "high"})
        assert "alerted" in result.lower()

    @pytest.mark.asyncio
    async def test_flag_transaction(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN
        )
        result = await executor._flag_transaction(incident, {"transaction_id": "tx123"})
        assert "flagged" in result.lower()

    @pytest.mark.asyncio
    async def test_suspend_account(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN
        )
        result = await executor._suspend_account(incident, {"user_id": "user123", "duration": "24h"})
        assert "suspended" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        executor = IncidentActionExecutor.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN
        )
        with pytest.raises(ValueError, match="Unknown action"):
            await executor.execute("unknown_action", incident, {})


class TestIncidentPlaybook:
    @pytest.mark.asyncio
    async def test_execute_empty_steps(self):
        playbook = IncidentPlaybook(
            name="Test Playbook",
            description="Empty playbook",
            steps=[]
        )
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN
        )
        results = await playbook.execute(incident)
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_with_steps(self):
        playbook = IncidentPlaybook(
            name="Test Playbook",
            description="Test",
            steps=[
                {"action": "alert_admin", "params": {"channel": "slack"}}
            ]
        )
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN
        )

        results = await playbook.execute(incident)
        assert len(results) == 1


class TestIncidentResponseEngine:
    def test_singleton(self):
        e1 = IncidentResponseEngine.get_instance()
        e2 = IncidentResponseEngine.get_instance()
        assert e1 is e2

    def test_default_rules(self):
        engine = IncidentResponseEngine.get_instance()
        assert len(engine.rules) > 0
        rule_names = [r.name for r in engine.rules]
        assert "multiple_failed_logins" in rule_names
        assert "spoofing_attempt" in rule_names
        assert "payment_fraud" in rule_names
        assert "model_drift" in rule_names

    def test_default_playbooks(self):
        engine = IncidentResponseEngine.get_instance()
        assert "failed_logins" in engine.playbooks
        assert "spoofing" in engine.playbooks
        assert "payment_fraud" in engine.playbooks
        assert "model_drift" in engine.playbooks

    @pytest.mark.asyncio
    async def test_evaluate_event_no_match(self):
        engine = IncidentResponseEngine.get_instance()
        event = {"event_type": "unknown_event", "count": 100}
        result = await engine.evaluate_event(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_event_match(self):
        engine = IncidentResponseEngine.get_instance()
        event = {"event_type": "login_failure", "count": 5, "window_minutes": 5}

        result = await engine.evaluate_event(event)
        assert result is not None
        assert "login" in result.title.lower()
        assert result.severity == IncidentSeverity.HIGH

    def test_evaluate_conditions_true(self):
        engine = IncidentResponseEngine()
        event = {"event_type": "test", "count": 10}
        conditions = {"event_type": "test", "count": 5}
        assert engine._evaluate_conditions(event, conditions) is True

    def test_evaluate_conditions_false_missing_key(self):
        engine = IncidentResponseEngine()
        event = {"event_type": "test"}
        conditions = {"event_type": "test", "missing": 5}
        assert engine._evaluate_conditions(event, conditions) is False

    def test_evaluate_conditions_false_low_value(self):
        engine = IncidentResponseEngine()
        event = {"event_type": "test", "count": 3}
        conditions = {"event_type": "test", "count": 5}
        assert engine._evaluate_conditions(event, conditions) is False

    @pytest.mark.asyncio
    async def test_update_incident_status(self):
        engine = IncidentResponseEngine.get_instance()
        incident = Incident(
            incident_id="INC-1",
            title="Test",
            description="Test",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN
        )
        engine.incidents["INC-1"] = incident

        result = await engine.update_incident_status("INC-1", IncidentStatus.RESOLVED, "Fixed")
        assert result.status == IncidentStatus.RESOLVED
        assert result.resolution_notes == "Fixed"

    def test_get_incidents_filter(self):
        engine = IncidentResponseEngine()
        engine.incidents = {
            "INC-1": Incident(incident_id="INC-1", title="Open", description="d", severity=IncidentSeverity.LOW, status=IncidentStatus.OPEN),
            "INC-2": Incident(incident_id="INC-2", title="Closed", description="d", severity=IncidentSeverity.LOW, status=IncidentStatus.CLOSED),
        }
        open_incidents = engine.get_incidents(IncidentStatus.OPEN)
        assert len(open_incidents) == 1
        assert open_incidents[0].incident_id == "INC-1"

    def test_get_incidents_all(self):
        engine = IncidentResponseEngine()
        engine.incidents = {
            "INC-1": Incident(incident_id="INC-1", title="Test", description="d", severity=IncidentSeverity.LOW, status=IncidentStatus.OPEN),
        }
        all_incidents = engine.get_incidents()
        assert len(all_incidents) == 1


class TestGlobalEngine:
    def test_incident_engine_exists(self):
        assert incident_engine is not None
        assert isinstance(incident_engine, IncidentResponseEngine)