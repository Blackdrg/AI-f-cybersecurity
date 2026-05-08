"""Enterprise integrations for AI-f - Okta, ServiceNow, PagerDuty, Splunk, Microsoft Sentinel"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import asyncio

logger = logging.getLogger(__name__)


class OktaIntegration:
    """Okta identity provider integration."""
    
    def __init__(self):
        self.domain = os.getenv("OKTA_DOMAIN")
        self.token = os.getenv("OKTA_API_TOKEN")
        self.base_url = f"https://{self.domain}/api/v1"
        self.headers = {
            "Authorization": f"SSWS {self.token}",
            "Content-Type": "application/json"
        }
    
    async def create_user(self, profile: Dict[str, Any]) -> Optional[str]:
        """Create user in Okta."""
        if not self.domain or not self.token:
            logger.warning("Okta not configured")
            return None
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/users",
                json={"profile": profile},
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json().get("id")
            logger.error(f"Okta create_user failed: {response.text}")
            return None
    
    async def assign_role(self, user_id: str, role_id: str) -> bool:
        """Assign role to user in Okta."""
        if not self.domain or not self.token:
            return False
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/users/{user_id}/roles/{role_id}",
                headers=self.headers
            )
            return response.status_code == 200


class ServiceNowIntegration:
    """ServiceNow ITSM integration."""
    
    def __init__(self):
        self.instance = os.getenv("SERVICENOW_INSTANCE")
        self.user = os.getenv("SERVICENOW_USER")
        self.password = os.getenv("SERVICENOW_PASSWORD")
        self.base_url = f"https://{self.instance}.service-now.com/api/now"
        self.auth = (self.user, self.password)
    
    async def create_incident(self, incident: Dict[str, Any]) -> Optional[str]:
        """Create incident in ServiceNow."""
        if not self.instance:
            logger.warning("ServiceNow not configured")
            return None
        
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/table/incident",
                json=incident,
                auth=self.auth,
                headers=headers
            )
            if response.status_code == 201:
                return response.json().get("result", {}).get("sys_id")
            logger.error(f"ServiceNow create_incident failed: {response.text}")
            return None
    
    async def update_incident(self, incident_id: str, updates: Dict[str, Any]) -> bool:
        """Update ServiceNow incident."""
        if not self.instance:
            return False
        
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/table/incident/{incident_id}",
                json=updates,
                auth=self.auth,
                headers=headers
            )
            return response.status_code == 200


class PagerDutyIntegration:
    """PagerDuty incident management integration."""
    
    def __init__(self):
        self.token = os.getenv("PAGERDUTY_TOKEN")
        self.base_url = "https://api.pagerduty.com"
        self.headers = {
            "Authorization": f"Token token={self.token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json"
        }
    
    async def trigger_incident(self, incident: Dict[str, Any]) -> Optional[str]:
        """Trigger PagerDuty incident."""
        if not self.token:
            logger.warning("PagerDuty not configured")
            return None
        
        payload = {
            "incident": {
                "type": "incident",
                "title": incident.get("title"),
                "service": {"id": os.getenv("PAGERDUTY_SERVICE_ID"), "type": "service_reference"},
                "body": {"type": "incident_body", "details": incident.get("details")}
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/incidents",
                json=payload,
                headers=self.headers
            )
            if response.status_code == 201:
                return response.json().get("incident", {}).get("id")
            logger.error(f"PagerDuty trigger failed: {response.text}")
            return None


class SplunkIntegration:
    """Splunk SIEM integration."""
    
    def __init__(self):
        self.host = os.getenv("SPLUNK_HOST")
        self.token = os.getenv("SPLUNK_TOKEN")
        self.base_url = f"https://{self.host}:8088/services/collector"
        self.headers = {"Authorization": f"Splunk {self.token}"}
    
    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event to Splunk."""
        if not self.host or not self.token:
            logger.warning("Splunk not configured")
            return False
        
        payload = {
            "time": int(datetime.utcnow().timestamp()),
            "event": event
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.base_url,
                json=payload,
                headers=self.headers
            )
            return response.status_code == 200


class MicrosoftSentinelIntegration:
    """Microsoft Sentinel integration."""
    
    def __init__(self):
        self.workspace_id = os.getenv("SENTINEL_WORKSPACE_ID")
        self.shared_key = os.getenv("SENTINEL_SHARED_KEY")
        self.base_url = f"https://{self.workspace_id}.ods.opinsights.azure.com/api/logs"
    
    async def send_log(self, log_type: str, data: Dict[str, Any]) -> bool:
        """Send log to Sentinel."""
        if not self.workspace_id or not self.shared_key:
            logger.warning("Sentinel not configured")
            return False
        
        import base64
        import hashlib
        import hmac
        
        json_data = json.dumps(data)
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        string_to_hash = f"POST\n{len(json_data)}\napplication/json\nx-ms-date:{date}\n/api/logs"
        bytes_to_hash = bytes(string_to_hash, "utf-8")
        key = bytes(self.shared_key, "utf-8")
        hashed = hmac.new(key, bytes_to_hash, hashlib.sha256).digest()
        signature = base64.b64encode(hashed).decode()
        
        headers = {
            "Authorization": f"SharedKey {self.workspace_id}:{signature}",
            "Log-Type": log_type,
            "x-ms-date": date,
            "time-generated-field": "timestamp"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                content=json_data,
                headers=headers
            )
            return response.status_code == 200


class CrowdStrikeIntegration:
    """CrowdStrike Falcon integration."""
    
    def __init__(self):
        self.client_id = os.getenv("CS_CLIENT_ID")
        self.client_secret = os.getenv("CS_CLIENT_SECRET")
        self.base_url = "https://api.crowdstrike.com"
        self.token = None
    
    async def authenticate(self) -> bool:
        """Authenticate with CrowdStrike."""
        if not self.client_id or not self.client_secret:
            return False
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            if response.status_code == 201:
                self.token = response.json().get("access_token")
                return True
            return False
    
    async def get_device_details(self, device_id: str) -> Optional[Dict]:
        """Get device details from CrowdStrike."""
        if not self.token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/devices/entities/devices/v1",
                params={"ids": device_id},
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return None


# Global integration instances
okta = OktaIntegration()
servicenow = ServiceNowIntegration()
pagerduty = PagerDutyIntegration()
splunk = SplunkIntegration()
sentinel = MicrosoftSentinelIntegration()
crowdstrike = CrowdStrikeIntegration()


async def send_to_integrations(event_type: str, data: Dict[str, Any]) -> Dict[str, bool]:
    """Send event to all configured integrations."""
    results = {}
    
    results["okta"] = await okta.create_user(data) is not None
    results["servicenow"] = await servicenow.create_incident(data) is not None
    results["pagerduty"] = await pagerduty.trigger_incident(data) is not None
    results["splunk"] = await splunk.send_event(data)
    results["sentinel"] = await sentinel.send_log(event_type, data)
    
    return results