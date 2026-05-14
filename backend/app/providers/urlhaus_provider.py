"""
URLhaus Integration - Malware URL database from abuse.ch
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class URLhausProvider:
    """URLhaus threat intelligence provider for malicious URLs."""

    BASE_URL = "https://urlhaus.abuse.ch"

    def __init__(self):
        self.enabled = bool(os.getenv("URLHAUS_API_KEY"))
        self.api_key = os.getenv("URLHAUS_API_KEY")
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

    async def lookup_url(self, url: str) -> Dict[str, Any]:
        """Check if a URL is listed in URLhaus."""
        if not self.enabled:
            return {"found": False, "error": "not_configured"}
        try:
            resp = await self._get_client().post(
                f"{self.BASE_URL}/downloads/csv/recent/",
                timeout=10.0
            )
            if resp.status_code != 200:
                return {"found": False, "error": f"api_error_{resp.status_code}"}

            # Parse CSV response
            text = resp.text
            lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.strip().startswith("#")]

            for line in lines:
                parts = line.split(",")
                if len(parts) >= 5 and url in parts[1]:
                    return {
                        "found": True,
                        "source": "urlhaus",
                        "url": parts[1] if len(parts) > 1 else "",
                        "url_status": parts[2] if len(parts) > 2 else "",
                        "threat": parts[3] if len(parts) > 3 else "",
                        "last_seen": parts[4] if len(parts) > 4 else "",
                        "threat_score": 85,
                        "tags": ["malware", "urlhaus"]
                    }

            return {"found": False, "source": "urlhaus"}
        except Exception as e:
            logger.error(f"URLhaus lookup failed for {url}: {e}")
            return {"found": False, "error": str(e)}

    async def get_fresh_list(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recently added malicious URLs from URLhaus."""
        if not self.enabled:
            return []

        try:
            resp = await self._get_client().post(
                f"{self.BASE_URL}/downloads/csv/recent/{hours}h/",
                timeout=15.0
            )
            if resp.status_code != 200:
                return []

            text = resp.text
            results = []
            lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.strip().startswith("#")]

            for line in lines:
                parts = line.split(",")
                if len(parts) >= 5:
                    threats = parts[3].split(" ") if len(parts) > 3 else []
                    results.append({
                        "url": parts[1] if len(parts) > 1 else "",
                        "url_status": parts[2] if len(parts) > 2 else "",
                        "threats": threats,
                        "last_seen": parts[4] if len(parts) > 4 else "",
                        "threat_score": 85,
                        "source": "urlhaus",
                        "ioc_type": "url",
                        "tags": ["malware", "urlhaus"]
                    })

            return results
        except Exception as e:
            logger.error(f"URLhaus fresh list fetch failed: {e}")
            return []

    async def get_health_status(self) -> str:
        """Return health status."""
        if not self.enabled:
            return "unconfigured"
        try:
            resp = await self._get_client().get(
                f"{self.BASE_URL}/",
                timeout=5.0
            )
            return "healthy" if resp.status_code == 200 else "degraded"
        except Exception:
            return "degraded"