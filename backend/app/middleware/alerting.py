"""
Production Alerting Middleware

Features:
- Severity-based routing (critical → PagerDuty/Pushover, high → Slack, medium → email)
- Alert throttling/debouncing (don't spam)
- Alert correlation (group similar alerts)
- Maintenance mode support
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import hashlib

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents a security/operational alert."""
    alert_id: str
    type: str
    severity: AlertSeverity
    message: str
    source: str
    details: Dict[str, Any] = field(default_factory=dict)
    status: AlertStatus = AlertStatus.NEW
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AlertCorrelator:
    """Groups similar alerts together."""

    def __init__(self, window_minutes: int = 5, threshold: int = 3):
        self.window = timedelta(minutes=window_minutes)
        self.threshold = threshold
        self._alert_groups: Dict[str, List[Alert]] = {}

    def correlate(self, alert: Alert) -> Optional[str]:
        """Return group ID if alert should be correlated."""
        key = self._get_alert_key(alert)
        now = datetime.utcnow()

        if key not in self._alert_groups:
            self._alert_groups[key] = []

        # Remove old alerts
        self._alert_groups[key] = [
            a for a in self._alert_groups[key]
            if now - a.created_at < self.window
        ]

        self._alert_groups[key].append(alert)

        if len(self._alert_groups[key]) >= self.threshold:
            return key  # Return group key for batch handling

        return None

    def _get_alert_key(self, alert: Alert) -> str:
        """Generate correlation key from alert properties."""
        return hashlib.md5(f"{alert.type}:{alert.source}".encode()).hexdigest()[:8]


class AlertThrottler:
    """Throttles duplicate alerts."""

    def __init__(self, cooldown_minutes: int = 15):
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self._last_sent: Dict[str, datetime] = {}

    def should_send(self, alert: Alert) -> bool:
        """Check if alert should be sent (not throttled)."""
        key = self._get_alert_key(alert)
        now = datetime.utcnow()

        if key in self._last_sent:
            if now - self._last_sent[key] < self.cooldown:
                return False

        self._last_sent[key] = now
        return True

    def _get_alert_key(self, alert: Alert) -> str:
        return f"{alert.type}:{alert.severity}"


class AlertRouter:
    """Routes alerts based on severity."""

    def __init__(self):
        self._routes = {
            AlertSeverity.CRITICAL: [
                ("pagerduty", os.getenv("PAGERDUTY_WEBHOOK_URL")),
                ("pushover", os.getenv("PUSHOVER_TOKEN")),
            ],
            AlertSeverity.HIGH: [
                ("slack", os.getenv("SLACK_ALERTS_WEBHOOK")),
            ],
            AlertSeverity.MEDIUM: [
                ("email", os.getenv("ALERTS_EMAIL")),
            ],
            AlertSeverity.LOW: [],
        }

    async def route(self, alert: Alert) -> List[str]:
        """Send alert to configured channels based on severity."""
        results = []
        channels = self._routes.get(alert.severity, [])

        for channel, config in channels:
            try:
                await self._send_to_channel(alert, channel, config)
                results.append(f"sent to {channel}")
            except Exception as e:
                logger.error(f"Failed sending to {channel}: {e}")
                results.append(f"failed {channel}: {e}")

        return results

    async def _send_to_channel(self, alert: Alert, channel: str, config: str):
        """Send alert to specific channel."""
        import httpx

        if channel == "pagerduty":
            await httpx.AsyncClient().post(config, json={
                "payload": {"summary": alert.message, "severity": "critical"},
                "routing_key": os.getenv("PAGERDUTY_ROUTING_KEY")
            })
        elif channel == "pushover":
            await httpx.AsyncClient().post("https://api.pushover.net/1/messages.json", json={
                "token": config,
                "user": os.getenv("PUSHOVER_USER"),
                "message": alert.message,
                "title": f"[{alert.severity}] {alert.type}"
            })
        elif channel == "slack":
            await httpx.AsyncClient().post(config, json={
                "text": f"[{alert.severity}] {alert.type}",
                "attachments": [{"text": alert.message, "color": "danger" if alert.severity == "critical" else "warning"}]
            })
        elif channel == "email":
            # Would integrate with email service
            logger.info(f"Email alert: {alert.message}")


class AlertingManager:
    """Central alert management with maintenance mode and correlation."""

    _instance = None
    MAINTENANCE_KEY = "alerts_maintenance_until"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.throttler = AlertThrottler()
        self.correlator = AlertCorrelator()
        self.router = AlertRouter()
        self.maintenance_until: Optional[datetime] = None
        self._alerts: Dict[str, Alert] = {}

    def set_maintenance_mode(self, duration_minutes: int = 60):
        """Enable maintenance mode for specified duration."""
        self.maintenance_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        logger.warning(f"Alert maintenance mode enabled for {duration_minutes} minutes")

    def clear_maintenance_mode(self):
        """Clear maintenance mode."""
        self.maintenance_until = None
        logger.info("Alert maintenance mode cleared")

    def is_maintenance(self) -> bool:
        """Check if currently in maintenance mode."""
        if not self.maintenance_until:
            return False
        return datetime.utcnow() < self.maintenance_until

    async def send_critical_alert(self, alert_type: str, details: Dict[str, Any]):
        """Send a critical alert with deduplication and routing."""
        alert = Alert(
            alert_id=f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            type=alert_type,
            severity=AlertSeverity.CRITICAL,
            message=details.get("message", alert_type),
            source=details.get("source", "system"),
            details=details
        )

        return await self.process_alert(alert)

    async def process_alert(self, alert: Alert) -> Dict[str, Any]:
        """Process alert with throttling, correlation, and routing."""
        # Check maintenance mode
        if self.is_maintenance():
            logger.info(f"Alert suppressed due to maintenance: {alert.type}")
            return {"status": "suppressed", "reason": "maintenance"}

        # Check throttling
        if not self.throttler.should_send(alert):
            logger.debug(f"Alert throttled: {alert.type}")
            return {"status": "throttled"}

        # Check correlation
        group_id = self.correlator.correlate(alert)
        if group_id:
            logger.info(f"Alert correlated into group: {group_id}")

        # Store alert
        self._alerts[alert.alert_id] = alert

        # Route and send
        results = await self.router.route(alert)

        return {
            "status": "sent",
            "alert_id": alert.alert_id,
            "channels": results,
            "correlated": group_id is not None
        }

    def acknowledge_alert(self, alert_id: str) -> Optional[Alert]:
        """Acknowledge an alert."""
        if alert_id not in self._alerts:
            return None
        alert = self._alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        if alert_id not in self._alerts:
            return None
        alert = self._alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        return alert

    def get_alerts(self, severity: Optional[AlertSeverity] = None,
                   status: Optional[AlertStatus] = None) -> List[Alert]:
        """Get alerts with optional filtering."""
        results = list(self._alerts.values())
        if severity:
            results = [a for a in results if a.severity == severity]
        if status:
            results = [a for a in results if a.status == status]
        return sorted(results, key=lambda a: a.created_at, reverse=True)


# Global instance
alerting_manager = AlertingManager.get_instance()


async def send_critical_alert(alert_type: str, details: Dict[str, Any]):
    """Convenience function for sending critical alerts."""
    return await alerting_manager.send_critical_alert(alert_type, details)