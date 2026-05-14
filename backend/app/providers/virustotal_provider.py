"""
Enhanced VirusTotal Integration
Supports file hash, URL, domain, and IP lookups with VirusTotal v3 API.
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class VirusTotalProvider:
    """Full VirusTotal v3 API integration for file, URL, domain, and IP lookups."""

    BASE_URL = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("VIRUS_TOTAL_API_KEY")
        self.headers = {"x-apikey": self.api_key} if self.api_key else {}
        self._client: Optional[httpx.AsyncClient] = None
        self.rate_limit_remaining = 1000
        self.rate_limit_reset = 0

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    # ─────────────────────────────────────────────
    # File Hash Lookup (Enhanced from existing)
    # ─────────────────────────────────────────────

    async def lookup_file_hash(self, file_hash: str) -> Dict[str, Any]:
        """Look up a file hash in VirusTotal. Supports MD5, SHA1, SHA256."""
        url = f"{self.BASE_URL}/files/{file_hash}"
        try:
            resp = await self._get_client().get(url, headers=self.headers)
            if resp.status_code == 404:
                return {"found": False, "error": "not_found"}
            if resp.status_code == 429:
                return {"found": False, "error": "rate_limited", "retry_after": self._parse_retry(resp)}
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return self._parse_file_response(data)
        except Exception as e:
            logger.error(f"VirusTotal file lookup failed for {file_hash}: {e}")
            return {"found": False, "error": str(e)}

    async def scan_file(self, file_content: bytes, filename: str = None) -> Dict[str, Any]:
        """Upload and scan a file with VirusTotal."""
        url = f"{self.BASE_URL}/files"
        try:
            files = {"file": (filename or "unknown", file_content, "application/octet-stream")}
            resp = await self._get_client().post(url, headers=self.headers, files=files)
            if resp.status_code == 429:
                return {"error": "rate_limited", "retry_after": self._parse_retry(resp)}
            resp.raise_for_status()
            result = resp.json().get("data", {})
            analysis_id = result.get("id")
            return {
                "scan_id": analysis_id,
                "status": "queued",
                "analysis_url": result.get("links", {}).get("self"),
                "message": "File uploaded for analysis"
            }
        except Exception as e:
            logger.error(f"VirusTotal file scan failed: {e}")
            return {"error": str(e)}

    async def get_file_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve results of a previously submitted file analysis."""
        url = f"{self.BASE_URL}/analyses/{analysis_id}"
        try:
            resp = await self._get_client().get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            attributes = data.get("attributes", {})
            return {
                "status": attributes.get("status", "unknown"),
                "stats": attributes.get("stats", {}),
                "results": attributes.get("results", {}),
                "category": attributes.get("category"),
                "meaningful_name": attributes.get("meaningful_name", "")
            }
        except Exception as e:
            logger.error(f"VirusTotal analysis retrieval failed: {e}")
            return {"error": str(e)}

    # ─────────────────────────────────────────────
    # URL Scanning (NEW)
    # ─────────────────────────────────────────────

    async def scan_url(self, url: str) -> Dict[str, Any]:
        """Submit a URL for scanning to VirusTotal."""
        api_url = f"{self.BASE_URL}/urls"
        try:
            resp = await self._get_client().post(
                api_url,
                headers=self.headers,
                data={"url": url}
            )
            if resp.status_code == 429:
                return {"error": "rate_limited", "retry_after": self._parse_retry(resp)}
            resp.raise_for_status()
            data = resp.json().get("data", {})
            analysis_id = data.get("id")
            return {
                "scan_id": analysis_id,
                "status": "queued",
                "analysis_url": data.get("links", {}).get("self"),
                "message": "URL submitted for analysis"
            }
        except Exception as e:
            logger.error(f"VirusTotal URL scan failed for {url}: {e}")
            return {"error": str(e)}

    async def get_url_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve URL scan results."""
        url = f"{self.BASE_URL}/analyses/{analysis_id}"
        try:
            resp = await self._get_client().get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            attributes = data.get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            return {
                "status": attributes.get("status", "unknown"),
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless": stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
                "total": sum(stats.values()),
                "malicious_ratio": stats.get("malicious", 0) / max(sum(stats.values()), 1),
                "categories": attributes.get("categories", {}),
                "meaningful_name": attributes.get("meaningful_name", ""),
                "title": attributes.get("title", ""),
                "tags": attributes.get("tags", []),
                "reputation": attributes.get("reputation", 0)
            }
        except Exception as e:
            logger.error(f"VirusTotal URL analysis retrieval failed: {e}")
            return {"error": str(e)}

    async def lookup_url_report(self, url: str) -> Dict[str, Any]:
        """Get latest report for a URL without re-scanning."""
        # URL needs to be base64-encoded for the report endpoint
        import base64
        encoded_url = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        api_url = f"{self.BASE_URL}/urls/{encoded_url}"
        try:
            resp = await self._get_client().get(api_url, headers=self.headers)
            if resp.status_code == 404:
                return {"found": False, "error": "not_found"}
            resp.raise_for_status()
            data = resp.json().get("data", {})
            attributes = data.get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            return {
                "found": True,
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "total": sum(stats.values()),
                "malicious_ratio": stats.get("malicious", 0) / max(sum(stats.values()), 1),
                "categories": attributes.get("categories", {}),
                "reputation": attributes.get("reputation", 0),
                "tags": attributes.get("tags", []),
                "title": attributes.get("title", ""),
                "meaningful_name": attributes.get("meaningful_name", "")
            }
        except Exception as e:
            logger.error(f"VirusTotal URL report lookup failed for {url}: {e}")
            return {"found": False, "error": str(e)}

    # ─────────────────────────────────────────────
    # Domain/IP Scanning (NEW)
    # ─────────────────────────────────────────────

    async def scan_domain(self, domain: str) -> Dict[str, Any]:
        """Submit a domain for scanning."""
        api_url = f"{self.BASE_URL}/domains/{domain}"
        try:
            resp = await self._get_client().get(api_url, headers=self.headers)
            if resp.status_code == 404:
                return {"found": False, "error": "not_found"}
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return self._parse_domain_response(data)
        except Exception as e:
            logger.error(f"VirusTotal domain scan failed for {domain}: {e}")
            return {"error": str(e)}

    async def get_domain_analysis(self, domain: str) -> Dict[str, Any]:
        """Get analysis results for a previously scanned domain."""
        return await self.scan_domain(domain)

    async def scan_ip(self, ip_address: str) -> Dict[str, Any]:
        """Submit an IP address for scanning."""
        api_url = f"{self.BASE_URL}/ip_addresses/{ip_address}"
        try:
            resp = await self._get_client().get(api_url, headers=self.headers)
            if resp.status_code == 404:
                return {"found": False, "error": "not_found"}
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return self._parse_ip_response(data)
        except Exception as e:
            logger.error(f"VirusTotal IP scan failed for {ip_address}: {e}")
            return {"error": str(e)}

    # ─────────────────────────────────────────────
    # Batch Operations (NEW)
    # ─────────────────────────────────────────────

    async def batch_lookup(self, indicators: List[str]) -> Dict[str, Dict[str, Any]]:
        """Look up multiple indicators in parallel."""
        import asyncio
        tasks = []
        for indicator in indicators:
            import re
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", indicator):
                tasks.append(self.scan_ip(indicator))
            elif re.match(r"^[a-fA-F0-9]{32,64}$", indicator):
                tasks.append(self.lookup_file_hash(indicator))
            else:
                tasks.append(self.scan_domain(indicator))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = {}
        for indicator, result in zip(indicators, results):
            if isinstance(result, Exception):
                output[indicator] = {"error": str(result)}
            else:
                output[indicator] = result
        return output

    # ─────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────

    def _parse_file_response(self, data: Dict) -> Dict[str, Any]:
        """Parse VirusTotal file response."""
        attributes = data.get("attributes", {})
        stats = attributes.get("last_analysis_stats", {})
        total = sum(stats.values())
        malicious = stats.get("malicious", 0)
        return {
            "found": True,
            "type_description": attributes.get("type_description", ""),
            "meaningful_name": attributes.get("meaningful_name", ""),
            "md5": attributes.get("md5", ""),
            "sha1": attributes.get("sha1", ""),
            "sha256": attributes.get("sha256", ""),
            "size": attributes.get("size", 0),
            "malicious": malicious,
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "total": total,
            "malicious_ratio": malicious / max(total, 1),
            "threat_score": int((malicious / max(total, 1)) * 100),
            "last_analysis_date": attributes.get("last_analysis_date"),
            "tags": attributes.get("popular_tags", []),
            "names": attributes.get("names", []),
            "tlsh": attributes.get("tlsh", ""),
            "pe_info": attributes.get("pe_info", {}),
            "exiftool": attributes.get("exiftool", {})
        }

    def _parse_domain_response(self, data: Dict) -> Dict[str, Any]:
        """Parse VirusTotal domain response."""
        attributes = data.get("attributes", {})
        stats = attributes.get("last_analysis_stats", {})
        total = sum(stats.values())
        malicious = stats.get("malicious", 0)
        return {
            "found": True,
            "domain": data.get("id", ""),
            "malicious": malicious,
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "total": total,
            "malicious_ratio": malicious / max(total, 1),
            "threat_score": int((malicious / max(total, 1)) * 100),
            "last_analysis_date": attributes.get("last_analysis_date"),
            "categories": attributes.get("categories", {}),
            "reputation": attributes.get("reputation", 0),
            "whois": attributes.get("whois", ""),
            "whois_date": attributes.get("whois_date"),
            "registrar": attributes.get("registrar", ""),
            "siblings": attributes.get("siblings", []),
            "subdomains": attributes.get("subdomains", []),
            "resolutions": attributes.get("last_dns_records", []),
            "tags": attributes.get("tags", []),
            "popularity_rank": attributes.get("popularity_rank", 0)
        }

    def _parse_ip_response(self, data: Dict) -> Dict[str, Any]:
        """Parse VirusTotal IP response."""
        attributes = data.get("attributes", {})
        stats = attributes.get("last_analysis_stats", {})
        total = sum(stats.values())
        malicious = stats.get("malicious", 0)
        return {
            "found": True,
            "ip": data.get("id", ""),
            "malicious": malicious,
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "total": total,
            "malicious_ratio": malicious / max(total, 1),
            "threat_score": int((malicious / max(total, 1)) * 100),
            "last_analysis_date": attributes.get("last_analysis_date"),
            "network": attributes.get("network", ""),
            "asn": attributes.get("asn", ""),
            "country": attributes.get("country", ""),
            "regional_internet_registry": attributes.get("regional_internet_registry", ""),
            "reputation": attributes.get("reputation", 0),
            "communicating_files": attributes.get("communicating_files", {}).get("data", []),
            "downloaded_files": attributes.get("downloaded_files", {}).get("data", []),
            "url_domains": attributes.get("url_domains", {}).get("data", []),
            "referrer_files": attributes.get("referrer_files", {}).get("data", []),
            "resolutions": attributes.get("resolutions", {}).get("data", []),
            "detected_urls": attributes.get("detected_urls", {}).get("data", []),
            "tags": attributes.get("tags", [])
        }

    def _parse_retry(self, resp: httpx.Response) -> int:
        """Parse retry-after header for rate limiting."""
        try:
            return int(resp.headers.get("retry-after", 60))
        except (ValueError, TypeError):
            return 60

    async def get_health_status(self) -> str:
        """Return health status based on configuration."""
        if not self.api_key:
            return "unconfigured"
        try:
            # Quick test call
            resp = await self._get_client().get(
                f"{self.BASE_URL}/files/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                headers=self.headers,
                timeout=5.0
            )
            if resp.status_code == 429:
                return "rate_limited"
            return "healthy"
        except Exception:
            return "degraded"