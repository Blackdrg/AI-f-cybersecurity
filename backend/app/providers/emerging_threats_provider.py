"""
Emerging Threats Integration - Threat intelligence from Proofpoint
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EmergingThreatsProvider:
    """Emerging Threats provider for indicators of compromise."""

    BASE_URL = "https://api.threatintelligence.Proofpoint.com"

    def __init__(self):
        self.enabled = bool(os.getenv("EMERGING_THREATS_API_KEY"))
        self.api_key = os.getenv("EMERGING_THREATS_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0)
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def is_configured(self) -> bool:
        return self.enabled

    async def search_ioc(self, indicator: str, ioc_type: str = "all") -> Dict[str, Any]:
        """Search for an indicator in Emerging Threats."""
        if not self.enabled:
            return {"found": False, "error": "not_configured"}

        try:
            headers = {
                "Authorization": f"TR {self.api_key}",
                "Accept": "application/json"
            }
            params = {"indicator": indicator}

            resp = await self._get_client().get(
                f"{self.BASE_URL}/v2/threat-intel",
                headers=headers,
                params=params,
                timeout=10.0
            )

            if resp.status_code == 404:
                return {"found": False, "source": "emerging_threats"}
            if resp.status_code == 401:
                return {"found": False, "error": "auth_failed", "source": "emerging_threats"}

            resp.raise_for_status()
            data = resp.json().get("data", {})

            return self._parse_response(data)
        except Exception as e:
            logger.error(f"Emerging Threats lookup failed for {indicator}: {e}")
            return {"found": False, "error": str(e), "source": "emerging_threats"}

    async def get_recent_threats(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent threats from Emerging Threats feed."""
        if not self.enabled:
            return []

        try:
            headers = {
                "Authorization": f"TR {self.api_key}",
                "Accept": "application/json"
            }
            params = {
                "days_back": days,
                "limit": limit
            }

            resp = await self._get_client().get(
                f"{self.BASE_URL}/v2/threat-intel/recent",
                headers=headers,
                params=params,
                timeout=15.0
            )

            resp.raise_for_status()
            data = resp.json().get("data", {}).get("threats", [])
            return [self._parse_response(t) for t in data]
        except Exception as e:
            logger.error(f"Emerging Threats recent threats fetch failed: {e}")
            return []

    async def get_pulse_feed(self, pulse_id: str) -> Dict[str, Any]:
        """Get a specific threat intelligence pulse."""
        if not self.enabled:
            return {"found": False, "error": "not_configured"}

        try:
            headers = {
                "Authorization": f"TR {self.api_key}",
                "Accept": "application/json"
            }

            resp = await self._get_client().get(
                f"{self.BASE_URL}/v2/pulse/{pulse_id}",
                headers=headers,
                timeout=10.0
            )

            if resp.status_code == 404:
                return {"found": False, "source": "emerging_threats"}

            resp.raise_for_status()
            data = resp.json().get("data", {})
            return {
                "found": True,
                "source": "emerging_threats",
                "pulse_id": pulse_id,
                "name": data.get("name", ""),
                "severity": data.get("severity", "medium"),
                "description": data.get("description", ""),
                "indicators": data.get("indicators", []),
                "created": data.get("created"),
                "updated": data.get("updated"),
                "threat_score": self._severity_to_score(data.get("severity", "medium")),
                "tags": data.get("tags", [])
            }
        except Exception as e:
            logger.error(f"Emerging Threats pulse fetch failed: {e}")
            return {"found": False, "error": str(e)}

    def _parse_response(self, data: Dict) -> Dict[str, Any]:
        """Parse Emerging Threats API response."""
        indicators = data.get("indicators", [])
        return {
            "found": True,
            "source": "emerging_threats",
            "indicator": data.get("indicator", ""),
            "type": data.get("type", "all"),
            "severity": data.get("severity", "medium"),
            "confidence": data.get("confidence", 0),
            "threat_score": self._severity_to_score(data.get("severity", "medium")),
            "malicious": data.get("malicious", False),
            "tags": data.get("tags", []),
            "first_seen": data.get("first_seen"),
            "last_seen": data.get("last_seen"),
            "related_pulses": data.get("related_pulses", []),
            "description": data.get("description", ""),
            "country": data.get("country"),
            "malware_family": data.get("malware_family"),
            "campaign": data.get("campaign")
        }

    @staticmethod
    def _severity_to_score(severity: str) -> int:
        """Convert severity string to numeric score."""
        mapping = {
            "low": 20,
            "suspicious": 40,
            "moderate": 60,
            "medium": 60,
            "high": 80,
            "critical": 100
        }
        return mapping.get(severity.lower(), 50)

    async def get_health_status(self) -> str:
        """Return health status."""
        if not self.enabled:
            return "unconfigured"
        try:
            headers = {"Authorization": f"TR {self.api_key}"}
            resp = await self._get_client().get(
                f"{self.BASE_URL}/health",
                headers=headers,
                timeout=5.0
            )
            return "healthy" if resp.status_code == 200 else "degraded"
        except Exception:
            return "degraded"