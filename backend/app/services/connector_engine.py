"""
Connector Engine
Generic connector framework for integrating with external security and IT systems.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class ConnectorType:
    """Supported connector types."""
    SIEM = "siem"
    TICKETING = "ticketing"
    NOTIFICATION = "notification"
    THREAT_INTEL = "threat_intel"
    IDENTITY = "identity"
    ENDPOINT = "endpoint"
    CLOUD = "cloud"
    CUSTOM_WEBHOOK = "custom_webhook"


class ConnectorStatus:
    """Connector health status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    UNCONFIGURED = "unconfigured"
    AUTH_ERROR = "auth_error"


class ConnectorEvent:
    """Event passed through connectors."""

    def __init__(self, event_type: str, data: Dict[str, Any],
                 metadata: Dict[str, Any] = None):
        self.event_type = event_type
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.correlation_id = data.get("correlation_id", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id
        }


class BaseConnector(ABC):
    """Abstract base class for all connectors."""

    def __init__(self, name: str, connector_type: str, config: Dict[str, Any]):
        self.name = name
        self.connector_type = connector_type
        self.config = config
        self.status = ConnectorStatus.UNCONFIGURED
        self._last_error: Optional[str] = None
        self._connected_at: Optional[str] = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external system."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection to the external system."""
        pass

    @abstractmethod
    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Send an event to the external system."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the connector."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get connector status information."""
        return {
            "name": self.name,
            "type": self.connector_type,
            "status": self.status,
            "last_error": self._last_error,
            "connected_at": self._connected_at
        }

    def _set_status(self, status: str, error: str = None):
        """Update connector status."""
        self.status = status
        self._last_error = error
        if status == ConnectorStatus.CONNECTED:
            self._connected_at = datetime.utcnow().isoformat()


class ServiceNowConnector(BaseConnector):
    """ServiceNow ITSM connector for incident management."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("servicenow", ConnectorType.TICKETING, config)
        self.instance = config.get("instance", os.getenv("SERVICENOW_INSTANCE"))
        self.username = config.get("username", os.getenv("SERVICENOW_USER"))
        self.password = config.get("password", os.getenv("SERVICENOW_PASSWORD"))

    async def connect(self) -> bool:
        try:
            test_url = f"https://{self.instance}.service-now.com/api/now/table/incident?sysparm_limit=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(test_url, auth=(self.username, self.password), timeout=10.0)
                self._set_status(ConnectorStatus.CONNECTED if resp.status_code == 200 else ConnectorStatus.AUTH_ERROR)
                return resp.status_code == 200
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return False

    async def disconnect(self):
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Create or update ServiceNow incident from event."""
        if self.status != ConnectorStatus.CONNECTED:
            return {"success": False, "error": "not_connected"}

        endpoint = self.config.get("endpoint", "/api/now/table/incident")
        url = f"https://{self.instance}.service-now.com{endpoint}"

        payload = {
            "short_description": event.event_type,
            "description": json.dumps(event.data, default=str),
            "urgency": self._severity_to_urgency(event.data.get("severity", "medium")),
            "category": "security",
            "subcategory": event.event_type,
            "correlation_id": event.correlation_id
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, auth=(self.username, self.password), json=payload, timeout=30.0)
                if resp.status_code in (200, 201):
                    data = resp.json().get("result", {})
                    return {"success": True, "ticket_id": data.get("number"), "sys_id": data.get("sys_id")}
                return {"success": False, "error": f"HTTP {resp.status_code}", "response": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            url = f"https://{self.instance}.service-now.com/api/now/table/sys_user?sysparm_limit=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, auth=(self.username, self.password), timeout=5.0)
                if resp.status_code == 200:
                    self._set_status(ConnectorStatus.CONNECTED)
                    return {"status": "healthy", "response_time_ms": resp.elapsed.total_seconds() * 1000}
                self._set_status(ConnectorStatus.AUTH_ERROR)
                return {"status": "auth_error", "http_code": resp.status_code}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def _severity_to_urgency(severity: str) -> int:
        return {"critical": 1, "high": 2, "medium": 3, "low": 4}.get(severity, 3)


class PagerDutyConnector(BaseConnector):
    """PagerDuty connector for incident alerting and on-call management."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("pagerduty", ConnectorType.NOTIFICATION, config)
        self.token = config.get("token", os.getenv("PAGERDUTY_TOKEN"))
        self.service_id = config.get("service_id", os.getenv("PAGERDUTY_SERVICE_ID"))

    async def connect(self) -> bool:
        try:
            headers = self._headers()
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.pagerduty.com/users/me", headers=headers, timeout=10.0)
                self._set_status(ConnectorStatus.CONNECTED if resp.status_code == 200 else ConnectorStatus.AUTH_ERROR)
                return resp.status_code == 200
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return False

    async def disconnect(self):
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Trigger a PagerDuty incident."""
        if self.status != ConnectorStatus.CONNECTED:
            return {"success": False, "error": "not_connected"}

        severity = event.data.get("severity", "warning")
        dedup_key = event.correlation_id or event.event_type

        payload = {
            "incident": {
                "type": "incident",
                "title": f"[{severity.upper()}] {event.event_type}",
                "service": {"id": self.service_id, "type": "service_reference"},
                "body": {"type": "incident_body", "details": json.dumps(event.data, default=str, indent=2)},
                "urgency": severity if severity in ("high", "low") else "warning",
                "dedup_key": dedup_key
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://api.pagerduty.com/incidents", json=payload, headers=self._headers(), timeout=15.0)
                if resp.status_code in (200, 201):
                    data = resp.json().get("incident", {})
                    return {"success": True, "incident_id": data.get("id"), "incident_number": data.get("incident_number")}
                return {"success": False, "error": f"HTTP {resp.status_code}", "response": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            headers = self._headers()
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.pagerduty.com/extensions/schema", headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    self._set_status(ConnectorStatus.CONNECTED)
                    return {"status": "healthy"}
                self._set_status(ConnectorStatus.AUTH_ERROR)
                return {"status": "auth_error", "http_code": resp.status_code}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return {"status": "unhealthy", "error": str(e)}

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token token={self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2"
        }


class SlackConnector(BaseConnector):
    """Slack connector for notifications and alerts."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("slack", ConnectorType.NOTIFICATION, config)
        self.webhook_url = config.get("webhook_url", os.getenv("SLACK_WEBHOOK_URL"))
        self.bot_token = config.get("bot_token", os.getenv("SLACK_BOT_TOKEN"))
        self.channel = config.get("channel", "#security-alerts")

    async def connect(self) -> bool:
        if not self.webhook_url:
            self._set_status(ConnectorStatus.UNCONFIGURED)
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json={"text": "Connectivity test"}, timeout=5.0)
                self._set_status(ConnectorStatus.CONNECTED if resp.status_code == 200 else ConnectorStatus.AUTH_ERROR)
                return resp.status_code == 200
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return False

    async def disconnect(self):
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Send notification to Slack."""
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            event.data.get("severity", "medium"), "⚪"
        )

        payload = {
            "channel": self.channel,
            "username": "AI-f Security Bot",
            "icon_emoji": ":shield:",
            "attachments": [{
                "color": {"critical": "#FF0000", "high": "#FF6600", "medium": "#FFCC00", "low": "#00CC00"}.get(
                    event.data.get("severity"), "#CCCCCC"
                ),
                "title": f"{severity_emoji} {event.event_type}",
                "text": json.dumps(event.data, default=str, indent=2)[:3000],
                "footer": f"AI-f Incident Response | {event.timestamp}",
                "ts": int(datetime.utcnow().timestamp())
            }]
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    return {"success": True, "channel": self.channel}
                return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json={"text": "health check"}, timeout=5.0)
                if resp.status_code == 200:
                    self._set_status(ConnectorStatus.CONNECTED)
                    return {"status": "healthy"}
                self._set_status(ConnectorStatus.AUTH_ERROR)
                return {"status": "auth_error"}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return {"status": "unhealthy", "error": str(e)}


class SplunkConnector(BaseConnector):
    """Splunk SIEM connector for event forwarding."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("splunk", ConnectorType.SIEM, config)
        self.host = config.get("host", os.getenv("SPLUNK_HOST"))
        self.token = config.get("token", os.getenv("SPLUNK_TOKEN"))
        self.source_type = config.get("source_type", "_json_alert")

    async def connect(self) -> bool:
        if not self.host or not self.token:
            self._set_status(ConnectorStatus.UNCONFIGURED)
            return False
        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(
                    f"https://{self.host}:8088/services/collector/health/1.0",
                    headers={"Authorization": f"Splunk {self.token}"},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    self._set_status(ConnectorStatus.CONNECTED)
                    return True
                self._set_status(ConnectorStatus.AUTH_ERROR)
                return False
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return False

    async def disconnect(self):
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Forward event to Splunk HTTP Event Collector."""
        url = f"https://{self.host}:8088/services/collector/event"
        payload = {
            "event": event.to_dict(),
            "sourcetype": self.source_type,
            "host": event.metadata.get("host", "ai-f-backend"),
            "source": f"ai-f-{event.event_type}"
        }

        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(url, json=payload, headers={"Authorization": f"Splunk {self.token}"}, timeout=10.0)
                if resp.status_code in (200, 204):
                    return {"success": True}
                return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(
                    f"https://{self.host}:8088/services/collector/health/1.0",
                    headers={"Authorization": f"Splunk {self.token}"},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    self._set_status(ConnectorStatus.CONNECTED)
                    return {"status": "healthy"}
                self._set_status(ConnectorStatus.DEGRADED)
                return {"status": "degraded", "http_code": resp.status_code}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return {"status": "unhealthy", "error": str(e)}


class CustomWebhookConnector(BaseConnector):
    """Generic outbound webhook connector."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("custom_webhook", ConnectorType.CUSTOM_WEBHOOK, config)
        self.url = config.get("url", "")
        self.headers = config.get("headers", {})
        self.method = config.get("method", "POST").upper()

    async def connect(self) -> bool:
        if not self.url:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(self.method, self.url, headers=self.headers, timeout=5.0)
                self._set_status(ConnectorStatus.CONNECTED if resp.status_code < 500 else ConnectorStatus.DEGRADED)
                return resp.status_code < 500
        except Exception:
            return False

    async def disconnect(self):
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Send event via webhook."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(self.method, self.url, json=event.to_dict(), headers=self.headers, timeout=15.0)
                return {"success": resp.status_code < 400, "http_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(self.method, self.url, headers=self.headers, timeout=5.0)
                self._set_status(ConnectorStatus.CONNECTED if resp.status_code < 500 else ConnectorStatus.DEGRADED)
                return {"status": self.status, "http_code": resp.status_code}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return {"status": "unhealthy", "error": str(e)}


class CrowdStrikeConnector(BaseConnector):
    """CrowdStrike Falcon connector for endpoint security."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("crowdstrike", ConnectorType.ENDPOINT, config)
        self.client_id = config.get("client_id", os.getenv("CS_CLIENT_ID"))
        self.client_secret = config.get("client_secret", os.getenv("CS_CLIENT_SECRET"))
        self.base_url = "https://api.crowdstrike.com"
        self._token = None
        self._token_expires = None

    async def _authenticate(self) -> bool:
        """Obtain OAuth2 token."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/oauth2/token",
                    data={"client_id": self.client_id, "client_secret": self.client_secret}
                )
                if resp.status_code == 201:
                    data = resp.json()
                    self._token = data.get("access_token")
                    expires_in = data.get("expires_in", 1799)
                    from datetime import timedelta
                    self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                    return True
        except Exception as e:
            logger.error(f"CrowdStrike auth failed: {e}")
        return False

    async def connect(self) -> bool:
        if not self.client_id or not self.client_secret:
            self._set_status(ConnectorStatus.UNCONFIGURED)
            return False
        success = await self._authenticate()
        self._set_status(ConnectorStatus.CONNECTED if success else ConnectorStatus.AUTH_ERROR)
        return success

    async def disconnect(self):
        self._token = None
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Send detection/alert to CrowdStrike."""
        if not self._token or datetime.utcnow() > self._token_expires:
            await self._authenticate()

        severity_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
        severity = severity_map.get(event.data.get("severity", "medium"), "medium")

        payload = {
            "body": {
                "ioa_id": event.correlation_id,
                "source": "ai-f",
                "severity": severity,
                "title": event.event_type,
                "description": json.dumps(event.data, default=str)[:4096]
            }
        }

        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            async with httpx.AsyncClient() as client:
                # Create detection
                resp = await client.post(f"{self.base_url}/detects/entities/detects/v1", json=payload, headers=headers, timeout=15.0)
                return {"success": resp.status_code == 200, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            await self._authenticate()
            if self._token:
                self._set_status(ConnectorStatus.CONNECTED)
                return {"status": "healthy", "token_expires": self._token_expires.isoformat()}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
        return {"status": self.status, "error": self._last_error}

    async def get_device_details(self, device_id: str) -> Dict[str, Any]:
        """Get details about a specific device."""
        if not self._token:
            return {"error": "not_authenticated"}
        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/devices/entities/devices/v1?ids={device_id}", headers=headers, timeout=10.0)
                return resp.json()
        except Exception as e:
            return {"error": str(e)}


class OktaConnector(BaseConnector):
    """Okta identity provider connector."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("okta", ConnectorType.IDENTITY, config)
        self.domain = config.get("domain", os.getenv("OKTA_DOMAIN"))
        self.token = config.get("token", os.getenv("OKTA_API_TOKEN"))
        self.base_url = f"https://{self.domain}/api/v1" if self.domain else ""

    async def connect(self) -> bool:
        if not self.base_url or not self.token:
            return False
        try:
            headers = {"Authorization": f"SSWS {self.token}", "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/users/me", headers=headers, timeout=5.0)
                self._set_status(ConnectorStatus.CONNECTED if resp.status_code == 200 else ConnectorStatus.AUTH_ERROR)
                return resp.status_code == 200
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return False

    async def disconnect(self):
        self._set_status(ConnectorStatus.DISCONNECTED)

    async def send_event(self, event: ConnectorEvent) -> Dict[str, Any]:
        """Send user action to Okta (suspend user, etc.)."""
        action = event.data.get("okta_action", "suspend_user")
        user_id = event.data.get("user_id", "")

        if not user_id:
            return {"success": False, "error": "no_user_id"}

        headers = {"Authorization": f"SSWS {self.token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                if action == "suspend_user":
                    resp = await client.post(f"{self.base_url}/users/{user_id}/lifecycle/suspend", headers=headers, timeout=10.0)
                elif action == "deactivate_user":
                    resp = await client.post(f"{self.base_url}/users/{user_id}/lifecycle/deactivate", headers=headers, timeout=10.0)
                elif action == "reset_password":
                    resp = await client.post(f"{self.base_url}/users/{user_id}/lifecycle/reset_password", headers=headers, timeout=10.0)
                elif action == "unlock_user":
                    resp = await client.post(f"{self.base_url}/users/{user_id}/lifecycle/unlock", headers=headers, timeout=10.0)
                else:
                    return {"success": False, "error": f"unknown_action: {action}"}

                return {"success": resp.status_code in (200, 204), "http_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            headers = {"Authorization": f"SSWS {self.token}", "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/users/me", headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    self._set_status(ConnectorStatus.CONNECTED)
                    return {"status": "healthy"}
                self._set_status(ConnectorStatus.AUTH_ERROR)
                return {"status": "auth_error"}
        except Exception as e:
            self._set_status(ConnectorStatus.DISCONNECTED, str(e))
            return {"status": "unhealthy", "error": str(e)}


class ConnectorRegistry:
    """Registry for managing all connectors."""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector):
        """Register a new connector."""
        self._connectors[connector.name] = connector

    def deregister(self, name: str):
        """Remove a connector by name."""
        self._connectors.pop(name, None)

    def get(self, name: str) -> Optional[BaseConnector]:
        """Get connector by name."""
        return self._connectors.get(name)

    def get_all(self) -> Dict[str, BaseConnector]:
        """Get all registered connectors."""
        return self._connectors.copy()

    def get_by_type(self, connector_type: str) -> List[BaseConnector]:
        """Get all connectors of a specific type."""
        return [c for c in self._connectors.values() if c.connector_type == connector_type]

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all registered connectors."""
        results = {}
        for name, connector in self._connectors.items():
            try:
                results[name] = await connector.connect()
            except Exception as e:
                logger.error(f"Failed to connect {name}: {e}")
                results[name] = False
        return results

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health check on all connectors."""
        results = {}
        for name, connector in self._connectors.items():
            try:
                results[name] = await connector.health_check()
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results

    async def send_event_to_all(self, event: ConnectorEvent) -> Dict[str, Dict[str, Any]]:
        """Send event to all connectors."""
        results = {}
        for name, connector in self._connectors.items():
            if connector.status == ConnectorStatus.CONNECTED:
                try:
                    results[name] = await connector.send_event(event)
                except Exception as e:
                    results[name] = {"success": False, "error": str(e)}
            else:
                results[name] = {"success": False, "error": f"connector status: {connector.status}"}
        return results

    async def disconnect_all(self):
        """Disconnect all connectors."""
        for connector in self._connectors.values():
            try:
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Failed to disconnect {connector.name}: {e}")

    def get_status_all(self) -> List[Dict[str, Any]]:
        """Get status of all connectors."""
        return [c.get_status() for c in self._connectors.values()]


# Global registry singleton
_connector_registry: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    """Get or create global connector registry."""
    global _connector_registry
    if _connector_registry is None:
        _connector_registry = ConnectorRegistry()
        _initialize_default_connectors(_connector_registry)
    return _connector_registry


def _initialize_default_connectors(registry: ConnectorRegistry):
    """Initialize default connectors from environment."""
    # ServiceNow
    if os.getenv("SERVICENOW_INSTANCE"):
        registry.register(ServiceNowConnector({}))

    # PagerDuty
    if os.getenv("PAGERDUTY_TOKEN"):
        registry.register(PagerDutyConnector({}))

    # Slack
    if os.getenv("SLACK_WEBHOOK_URL"):
        registry.register(SlackConnector({}))

    # Splunk
    if os.getenv("SPLUNK_HOST") and os.getenv("SPLUNK_TOKEN"):
        registry.register(SplunkConnector({}))

    # CrowdStrike
    if os.getenv("CS_CLIENT_ID") and os.getenv("CS_CLIENT_SECRET"):
        registry.register(CrowdStrikeConnector({}))

    # Okta
    if os.getenv("OKTA_DOMAIN") and os.getenv("OKTA_API_TOKEN"):
        registry.register(OktaConnector({}))


async def send_to_connector(connector_name: str, event: ConnectorEvent) -> Dict[str, Any]:
    """Send event to a specific connector by name."""
    registry = get_connector_registry()
    connector = registry.get(connector_name)
    if connector is None:
        return {"success": False, "error": f"connector '{connector_name}' not found"}
    return await connector.send_event(event)