"""Threat Intelligence Provider for real-time security feeds.

Integrates with external threat intel platforms:
- AlienVault OTX
- MISP (Malware Information Sharing Platform)
- VirusTotal (future)
- AbuseIPDB, URLhaus, Emerging Threats

Requires API keys in environment variables:
- OTX_API_KEY: AlienVault OTX API key
- MISP_URL, MISP_API_KEY: MISP instance URL and key
- VIRUSTOTAL_API_KEY: VirusTotal API key
- ABUSEIPDB_API_KEY: AbuseIPDB API key
- THREAT_INTEL_WEBHOOK_URL: Webhook for high-severity alerts
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import hashlib
import asyncio
from .base import BaseProvider

logger = logging.getLogger(__name__)

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600


class ThreatIntelProvider(BaseProvider):
    """Provider for real-time threat intelligence feeds with caching and IOC lookup."""

    def __init__(self):
        api_key = os.getenv("OTX_API_KEY") or os.getenv("MISP_API_KEY")
        super().__init__(name="threat_intel", api_key=api_key)
        self.otx_key = os.getenv("OTX_API_KEY")
        self.misp_url = os.getenv("MISP_URL")
        self.misp_key = os.getenv("MISP_API_KEY")
        self.vt_key = os.getenv("VIRUS_TOTAL_API_KEY")
        self.abuseipdb_key = os.getenv("ABUSEIPDB_API_KEY")
        self.webhook_url = os.getenv("THREAT_INTEL_WEBHOOK_URL")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Air-gapped mode check
        self.air_gapped = os.getenv("AIR_GAPPED", "false").lower() == "true"
        
        # Demo mode: use synthetic data for UI demos/dev when keys missing
        # Auto-enable in development if no keys configured
        env = os.getenv("ENVIRONMENT", "development").lower()
        explicit_demo = os.getenv("THREAT_INTEL_DEMO_MODE", "false").lower() == "true"
        
        # Auto-enable demo if in development and no API keys present
        keys_configured = any([self.otx_key, self.misp_key, self.vt_key, self.abuseipdb_key])
        self.demo_mode = explicit_demo or (env in ["development", "dev", "test"] and not keys_configured)
        
        if self.demo_mode:
            logger.info(
                "ThreatIntelProvider running in DEMO MODE — "
                "synthetic data only. Set OTX_API_KEY/MISP_API_KEY for real feeds."
            )
        elif not keys_configured and env in ["production", "prod"]:
            logger.warning(
                "ThreatIntelProvider: No API keys configured (OTX/MISP/VT). "
                "Feed will return empty. Set keys or set THREAT_INTEL_DEMO_MODE=true for demo data."
            )

    def _is_cached(self, key: str) -> bool:
        """Check if cached entry is still valid."""
        if key not in self._cache_timestamps:
            return False
        return datetime.utcnow() - self._cache_timestamps[key] < timedelta(seconds=CACHE_TTL)

    def _set_cache(self, key: str, value: Any):
        """Set cache entry with timestamp."""
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.utcnow()

    def _get_cache(self, key: str) -> Optional[Any]:
        """Get cached value if still valid."""
        if self._is_cached(key):
            return self._cache.get(key)
        return None

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search threat intelligence feeds for indicators related to query.

        Args:
            query: Search term (person name, hash, IP, etc.)
            limit: Max results per source

        Returns:
            List of threat intel results
        """
        if self.air_gapped:
            return []  # Air-gapped mode disables external calls
        if self.demo_mode:
            return self._get_demo_search_results(query, limit)
        cached = self._get_cache(f"search:{query}")
        if cached:
            return cached

        results = []
        # Search OTX if configured
        if self.otx_key:
            try:
                otx_results = await self._search_otx(query, limit)
                results.extend(otx_results)
            except Exception as e:
                logger.error(f"OTX search error: {e}")

        # Search MISP if configured
        if self.misp_url and self.misp_key:
            try:
                misp_results = await self._search_misp(query, limit)
                results.extend(misp_results)
            except Exception as e:
                logger.error(f"MISP search error: {e}")

        # Deduplicate by URL and limit overall
        seen = set()
        deduped = []
        for r in results:
            url = r.get("url", "")
            if url and url not in seen:
                seen.add(url)
                deduped.append(r)
                if len(deduped) >= limit:
                    break

        self._set_cache(f"search:{query}", deduped)
        return deduped

    async def lookup_ioc(self, indicator: str, ioc_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Lookup an indicator of compromise (IP, domain, hash, user agent).

        Args:
            indicator: The IOC value to lookup
            ioc_type: Type hint (ip, domain, hash, user_agent). Auto-detected if None.

        Returns:
            Threat intel result with score 0-100
        """
        cached = self._get_cache(f"ioc:{indicator}")
        if cached:
            return cached

        # Demo mode stub
        if self.demo_mode:
            ioc_type = ioc_type or self._detect_ioc_type(indicator)
            result = self._get_demo_ioc_result(indicator, ioc_type)
            self._set_cache(f"ioc:{indicator}", result)
            return result

        # Auto-detect IOC type
        if not ioc_type:
            ioc_type = self._detect_ioc_type(indicator)

        result = {
            "indicator": indicator,
            "type": ioc_type,
            "threat_score": 0,
            "sources": [],
            "last_seen": None,
            "tags": [],
            "malicious": False
        }

        tasks = []
        if ioc_type == "ip" and self.abuseipdb_key:
            tasks.append(self._lookup_abuseipdb(indicator))
        if ioc_type in ("ip", "domain") and self.otx_key:
            tasks.append(self._lookup_otx_ioc(indicator, ioc_type))
        if ioc_type == "hash" and self.vt_key:
            tasks.append(self._lookup_virustotal(indicator))

        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            max_score = 0
            for resp in responses:
                if isinstance(resp, dict):
                    result["sources"].append(resp.get("source", "unknown"))
                    result["tags"].extend(resp.get("tags", []))
                    if resp.get("last_seen"):
                        result["last_seen"] = resp["last_seen"]
                    max_score = max(max_score, resp.get("score", 0))

            result["threat_score"] = max_score
            result["malicious"] = max_score >= 50

        self._set_cache(f"ioc:{indicator}", result)
        return result

    def _detect_ioc_type(self, indicator: str) -> str:
        """Auto-detect IOC type from value."""
        import re
        # IPv4
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", indicator):
            return "ip"
        # Domain
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,}$", indicator):
            return "domain"
        # Hash (MD5, SHA1, SHA256)
        if re.match(r"^[a-fA-F0-9]{32,64}$", indicator):
            return "hash"
        return "unknown"

    async def _search_otx(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Query AlienVault OTX pulses."""
        url = "https://otx.alienvault.com/api/v1/search/pulses"
        params = {"q": query, "limit": limit, "sort": "-modified"}
        headers = {"X-OTX-API-KEY": self.otx_key}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for pulse in data.get("results", []):
                    results.append({
                        "id": f"otx_{pulse.get('id')}",
                        "provider": "otx",
                        "providerName": "AlienVault OTX",
                        "title": pulse.get("name", "Threat Pulse"),
                        "snippet": (pulse.get("description", "") or "")[:250],
                        "url": f"https://otx.alienvault.com/pulse/{pulse.get('id')}",
                        "confidence": 0.85,
                        "type": "threat_intelligence",
                        "timestamp": pulse.get("modified", ""),
                        "tags": pulse.get("tags", []),
                        "severity": pulse.get("tlp", "amber")
                    })
                return results
        except Exception as e:
            logger.error(f"OTX request failed: {e}")
            return []

    async def _search_misp(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Query MISP via REST API for events."""
        url = f"{self.misp_url.rstrip('/')}/events/restSearch"
        headers = {
            "Authorization": self.misp_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "returnFormat": "json",
            "limit": limit,
            "page": 1,
            "value": query
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for event in data.get("response", []):
                    ev = event.get("Event", {})
                    results.append({
                        "id": f"misp_{ev.get('id')}",
                        "provider": "misp",
                        "providerName": "MISP",
                        "title": ev.get("info", "MISP Event"),
                        "snippet": ev.get("date", ""),
                        "url": f"{self.misp_url}/events/view/{ev.get('id')}",
                        "confidence": 0.9,
                        "type": "threat_intelligence",
                        "timestamp": ev.get("date", ""),
                        "tags": [t["name"] for t in ev.get("Tag", []) if "name" in t],
                        "severity": "high"
                    })
                return results
        except Exception as e:
            logger.error(f"MISP request failed: {e}")
            return []

    async def _lookup_abuseipdb(self, ip: str) -> Dict[str, Any]:
        """Lookup IP in AbuseIPDB."""
        url = "https://api.abuseipdb.com/api/v2/check"
        headers = {"Key": self.abuseipdb_key, "Accept": "application/json"}
        params = {"ipAddress": ip, "maxAgeInDays": 90}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers, timeout=10.0)
                resp.raise_for_status()
                data = resp.json().get("data", {})
                score = min(100, data.get("abuseConfidenceScore", 0) * 2)  # Scale to 0-100
                return {
                    "source": "AbuseIPDB",
                    "score": score,
                    "tags": data.get("usageType", []) if isinstance(data.get("usageType"), list) else [data.get("usageType")] if data.get("usageType") else [],
                    "last_seen": data.get("lastReportedAt")
                }
        except Exception as e:
            logger.error(f"AbuseIPDB lookup failed: {e}")
            return {"source": "AbuseIPDB", "score": 0, "tags": [], "last_seen": None}

    async def _lookup_otx_ioc(self, indicator: str, ioc_type: str) -> Dict[str, Any]:
        """Lookup IOC in OTX."""
        url = f"https://otx.alienvault.com/api/v1/indicators/{ioc_type}/{indicator}/general"
        headers = {"X-OTX-API-KEY": self.otx_key}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 404:
                    return {"source": "OTX", "score": 0, "tags": [], "last_seen": None}
                resp.raise_for_status()
                data = resp.json()
                pulse_info = data.get("pulse_info", {})
                score = min(100, len(pulse_info.get("pulses", [])) * 10)
                return {
                    "source": "OTX",
                    "score": score,
                    "tags": [p.get("tags", []) for p in pulse_info.get("pulses", [])],
                    "last_seen": data.get("updated")
                }
        except Exception as e:
            logger.error(f"OTX IOC lookup failed: {e}")
            return {"source": "OTX", "score": 0, "tags": [], "last_seen": None}

    async def _lookup_virustotal(self, file_hash: str) -> Dict[str, Any]:
        """Lookup hash in VirusTotal."""
        url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
        headers = {"x-apikey": self.vt_key}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 404:
                    return {"source": "VirusTotal", "score": 0, "tags": [], "last_seen": None}
                resp.raise_for_status()
                data = resp.json().get("data", {}).get("attributes", {})
                stats = data.get("last_analysis_stats", {})
                malicious = stats.get("malicious", 0)
                total = sum(stats.values())
                score = int((malicious / total * 100) if total > 0 else 0)
                return {
                    "source": "VirusTotal",
                    "score": score,
                    "tags": data.get("popular_tags", []),
                    "last_seen": data.get("last_analysis_date")
                }
        except Exception as e:
            logger.error(f"VirusTotal lookup failed: {e}")
            return {"source": "VirusTotal", "score": 0, "tags": [], "last_seen": None}

    async def send_webhook_alert(self, event: Dict[str, Any], severity: str = "high"):
        """Send webhook notification for high-severity threats."""
        if not self.webhook_url:
            logger.warning("No webhook URL configured for threat alerts")
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.webhook_url,
                    json={
                        "event": event,
                        "severity": severity,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "threat_intel"
                    },
                    timeout=5.0
                )
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")

    async def block_ip(self, ip: str, reason: str = "Threat intelligence") -> bool:
        """Integrate with rate limiter to block malicious IP."""
        from .rate_limit import rate_limiter_middleware
        if rate_limiter_middleware and rate_limiter_middleware.limiter:
            try:
                await rate_limiter_middleware.limiter.block_ip(ip, reason=reason)
                return True
            except Exception as e:
                logger.error(f"Failed to block IP {ip}: {e}")
        return False

    async def get_health_status(self) -> str:
        """Return health based on configuration."""
        if self.otx_key or (self.misp_url and self.misp_key):
            return "healthy"
        return "unconfigured"

    async def update_cache(self):
        """Background task to refresh cached data."""
        # Clear expired cache entries
        now = datetime.utcnow()
        expired = [k for k, v in self._cache_timestamps.items()
                   if now - v >= timedelta(seconds=CACHE_TTL)]
        for k in expired:
            self._cache.pop(k, None)
            self._cache_timestamps.pop(k, None)

    # ------------------------------------------------------------------------
    # Demo / Stub Data Mode
    # ------------------------------------------------------------------------
    def _get_demo_search_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Generate synthetic threat intel results for demo/development."""
        demo_items = [
            {
                "id": "demo_otx_1",
                "provider": "otx",
                "providerName": "AlienVault OTX (Demo)",
                "title": f"Sample Threat Pulse related to '{query}'",
                "snippet": f"This is a demonstration threat pulse for '{query}'. In production, real OTX data would appear here after configuring OTX_API_KEY.",
                "url": "https://otx.alienvault.com/pulse/demo",
                "severity": "medium",
                "score": 65,
                "tags": ["demo", "threat", "sample"],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "demo_misp_1",
                "provider": "misp",
                "providerName": "MISP (Demo)",
                "title": f"Mock MISP Event: {query}",
                "snippet": "Simulated MISP event for UI demonstration. No actual threat data.",
                "url": "https://misp.example.com/event/12345",
                "severity": "high",
                "score": 85,
                "tags": ["misp", "indicators", "demo"],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "demo_generic_1",
                "provider": "generic",
                "providerName": "Generic Threat Feed (Demo)",
                "title": f"Suspicious activity: {query}",
                "snippet": "This is placeholder threat intelligence. Configure real API keys for production data.",
                "url": None,
                "severity": "low",
                "score": 30,
                "tags": ["generic", "demo"],
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        return demo_items[:limit]

    def _get_demo_ioc_result(self, indicator: str, ioc_type: str) -> Dict[str, Any]:
        """Generate synthetic IOC lookup result for demo."""
        return {
            "indicator": indicator,
            "type": ioc_type,
            "threat_score": 42,
            "sources": ["demo"],
            "last_seen": datetime.utcnow().isoformat(),
            "tags": ["demo", "simulated"],
            "malicious": False
        }