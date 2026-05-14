"""
Updated Threat Intel Provider with enhanced integrations and caching.
Integrates VirusTotal, MISP, OTX, URLhaus, Emerging Threats, and STIX/TAXII.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import asyncio
import httpx

from .base import BaseProvider
from .ioc_repository import IOCRepository, IOC, IOCSource, IOCSeverity, IOCStatus

logger = logging.getLogger(__name__)

CACHE_TTL = 3600


class ThreatIntelProvider(BaseProvider):
    """Enhanced provider with full integration for all threat intelligence platforms."""

    def __init__(self):
        api_key = os.getenv("OTX_API_KEY") or os.getenv("MISP_API_KEY")
        super().__init__(name="threat_intel", api_key=api_key)
        self.otx_key = os.getenv("OTX_API_KEY")
        self.misp_url = os.getenv("MISP_URL")
        self.misp_key = os.getenv("MISP_API_KEY")
        self.vt_key = os.getenv("VIRUS_TOTAL_API_KEY")
        self.abuseipdb_key = os.getenv("ABUSEIPDB_API_KEY")
        self.webhook_url = os.getenv("THREAT_INTEL_WEBHOOK_URL")

        # Initialize integrations
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

        # VirusTotal (full integration)
        self.vt_client = None
        if self.vt_key:
            try:
                from app.providers.virustotal_provider import VirusTotalProvider
                self.vt_client = VirusTotalProvider(self.vt_key)
            except Exception as e:
                logger.warning(f"VirusTotal initialization failed: {e}")

        # URLhaus
        self.urlhaus_client = None
        if os.getenv("URLHAUS_API_KEY"):
            try:
                from app.providers.urlhaus_provider import URLhausProvider
                self.urlhaus_client = URLhausProvider()
            except Exception as e:
                logger.warning(f"URLhaus initialization failed: {e}")

        # Emerging Threats
        self.et_client = None
        if os.getenv("EMERGING_THREATS_API_KEY"):
            try:
                from app.providers.emerging_threats_provider import EmergingThreatsProvider
                self.et_client = EmergingThreatsProvider()
            except Exception as e:
                logger.warning(f"Emerging Threats initialization failed: {e}")

        # STIX/TAXII
        self.taxii_enabled = bool(os.getenv("TAXII_URL"))
        if self.taxii_enabled:
            try:
                from app.providers.stix_taxii_provider import STIXTaxiiClient
                self.taxii_client = STIXTaxiiClient(
                    base_url=os.getenv("TAXII_URL", ""),
                    collection_id=os.getenv("TAXII_COLLECTION_ID")
                )
            except Exception as e:
                logger.warning(f"TAXII initialization failed: {e}")
                self.taxii_enabled = False

        # IOC Repository
        self.ioc_repo = None
        try:
            self.ioc_repo = IOCRepository()
        except Exception:
            pass

        # Air-gapped mode check
        self.air_gapped = os.getenv("AIR_GAPPED", "false").lower() == "true"

        # Demo mode
        env = os.getenv("ENVIRONMENT", "development").lower()
        explicit_demo = os.getenv("THREAT_INTEL_DEMO_MODE", "false").lower() == "true"
        keys_configured = any([self.otx_key, self.misp_key, self.vt_key, self.abuseipdb_key])
        self.demo_mode = explicit_demo or (env in ["development", "dev", "test"] and not keys_configured)

        if self.demo_mode:
            logger.info("ThreatIntelProvider running in DEMO MODE")
        elif not keys_configured and env in ["production", "prod"]:
            logger.warning("No API keys configured for threat intelligence")

    async def initialize(self):
        """Initialize all connections and create database tables."""
        if self.ioc_repo:
            try:
                await self.ioc_repo.initialize()
                await self.ioc_repo.create_tables()
                logger.info("IOC repository initialized successfully")
            except Exception as e:
                logger.warning(f"IOC repository initialization failed: {e}")

    # ──────────────────────────────────────────
    # Public API (enhanced)
    # ──────────────────────────────────────────

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search threat intelligence feeds for indicators related to query."""
        if self.air_gapped:
            return []
        if self.demo_mode:
            return self._get_demo_search_results(query, limit)

        cached = self._get_cache(f"search:{query}")
        if cached:
            return cached

        results = []

        # Search OTX
        if self.otx_key:
            try:
                results.extend(await self._search_otx(query, limit))
            except Exception as e:
                logger.error(f"OTX search error: {e}")

        # Search MISP
        if self.misp_url and self.misp_key:
            try:
                results.extend(await self._search_misp(query, limit))
            except Exception as e:
                logger.error(f"MISP search error: {e}")

        # Search Emerging Threats
        if self.et_client and self.et_client.is_configured():
            try:
                et_results = await self.et_client.search_ioc(query)
                if et_results.get("found"):
                    results.append({
                        "id": f"et_{et_results.get('indicator', query)}",
                        "provider": "emerging_threats",
                        "providerName": "Emerging Threats",
                        "title": et_results.get("description", f"Threat: {query}"),
                        "snippet": et_results.get("description", "")[:250],
                        "url": None,
                        "confidence": et_results.get("confidence", 0),
                        "type": "threat_intelligence",
                        "timestamp": et_results.get("last_seen"),
                        "tags": et_results.get("tags", []),
                        "severity": self._score_to_severity(et_results.get("threat_score", 0))
                    })
            except Exception as e:
                logger.error(f"Emerging Threats search error: {e}")

        # Search internal IOC database
        if self.ioc_repo:
            try:
                db_results = await self.ioc_repo.lookup(query)
                for db_ioc in db_results[:5]:
                    results.append({
                        "id": f"internal_{db_ioc.get('ioc_id', '')}",
                        "provider": "internal",
                        "providerName": "Internal IOC Database",
                        "title": f"{db_ioc.get('ioc_type')}: {db_ioc.get('indicator')}",
                        "snippet": db_ioc.get("description", "")[:250],
                        "url": None,
                        "confidence": float(db_ioc.get("confidence", 0)),
                        "type": "threat_intelligence",
                        "timestamp": db_ioc.get("last_seen", ""),
                        "tags": db_ioc.get("tags", []),
                        "severity": db_ioc.get("severity", "medium"),
                        "threat_score": db_ioc.get("threat_score", 0)
                    })
            except Exception as e:
                logger.error(f"Internal IOC search error: {e}")

        # Deduplicate
        seen = set()
        deduped = []
        for r in results:
            url = r.get("url", r.get("title", ""))
            if url and url not in seen:
                seen.add(url)
                deduped.append(r)
                if len(deduped) >= limit:
                    break

        self._set_cache(f"search:{query}", deduped)
        return deduped

    async def lookup_ioc(self, indicator: str, ioc_type: Optional[str] = None) -> Dict[str, Any]:
        """Lookup IOC across all available sources with caching."""
        # Check internal database first
        db_result = await self._lookup_internal_db(indicator, ioc_type)

        # Check in-memory cache
        cached = self._get_cache(f"ioc:{indicator}")
        if cached and not db_result.get("needs_refresh", False):
            return cached

        # Demo mode
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
            "details": {},
            "last_seen": None,
            "tags": [],
            "malicious": False,
            "lookup_timestamp": datetime.utcnow().isoformat()
        }

        # Parallel lookups across all available sources
        tasks = []

        if ioc_type == "ip" and self.abuseipdb_key:
            tasks.append(self._lookup_abuseipdb(indicator))

        if ioc_type in ("ip", "domain") and self.otx_key:
            tasks.append(self._lookup_otx_ioc(indicator, ioc_type))

        if ioc_type == "hash" and self.vt_key:
            tasks.append(self._lookup_virustotal(indicator))

        # Enhanced URL/Domain lookups
        if ioc_type == "url" and self.vt_client:
            tasks.append(self._lookup_vt_url(indicator))

        if ioc_type == "domain" and self.vt_client:
            tasks.append(self._lookup_vt_domain(indicator))

        if ioc_type == "url" and self.urlhaus_client and self.urlhaus_client.is_configured():
            tasks.append(self._lookup_urlhaus(indicator))

        # Generic lookup for any type via Emerging Threats
        if self.et_client and self.et_client.is_configured():
            tasks.append(self._lookup_emerging_threats(indicator, ioc_type))

        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for resp in responses:
                if isinstance(resp, dict) and not isinstance(resp, Exception):
                    source = resp.get("source", "unknown")
                    score = resp.get("score", 0) or resp.get("threat_score", 0)

                    result["sources"].append(source)
                    result["details"][source] = {
                        "score": score,
                        "tags": resp.get("tags", []),
                        "raw": {k: v for k, v in resp.items()
                               if k not in ("source", "score", "tags")}
                    }

                    if resp.get("tags"):
                        result["tags"].extend(resp.get("tags", []))
                    if resp.get("last_seen"):
                        if not result["last_seen"] or resp["last_seen"] > result["last_seen"]:
                            result["last_seen"] = resp["last_seen"]

                    if score > result["threat_score"]:
                        result["threat_score"] = score
                        result["malicious"] = score >= 50

        # Merge with database result
        if db_result.get("found"):
            db_score = db_result.get("threat_score", 0)
            if db_score > result["threat_score"]:
                result["threat_score"] = db_score
                result["malicious"] = db_score >= 50
            result["tags"] = list(set(result["tags"] + db_result.get("tags", [])))
            if db_result.get("last_seen"):
                if not result["last_seen"] or db_result["last_seen"] > result["last_seen"]:
                    result["last_seen"] = db_result["last_seen"]

        self._set_cache(f"ioc:{indicator}", result)

        # Persist to database for future lookups
        if self.ioc_repo and result["threat_score"] > 0:
            await self._persist_ioc(indicator, ioc_type, result)

        return result

    async def enrich_batch(self, indicators: List[tuple]) -> List[Dict[str, Any]]:
        """Enrich multiple IOCs in batch."""
        tasks = [self.lookup_ioc(ind, itype) for ind, itype in indicators]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # ──────────────────────────────────────────
    # Source-specific lookups (enhanced)
    # ──────────────────────────────────────────

    async def _lookup_vt_url(self, url: str) -> Dict[str, Any]:
        """Enhanced VT URL lookup."""
        if not self.vt_client:
            return {"source": "virustotal", "score": 0}
        try:
            result = await self.vt_client.lookup_url_report(url)
            if result.get("found"):
                return {
                    "source": "virustotal",
                    "score": result.get("malicious_ratio", 0) * 100,
                    "tags": result.get("tags", []),
                    "categories": result.get("categories", {}),
                    "last_seen": result.get("last_analysis_date"),
                    "reputation": result.get("reputation", 0),
                    "malicious": result.get("malicious", 0) > 0
                }
        except Exception as e:
            logger.error(f"VT URL lookup failed for {url}: {e}")
        return {"source": "virustotal", "score": 0}

    async def _lookup_vt_domain(self, domain: str) -> Dict[str, Any]:
        """Enhanced VT domain lookup."""
        if not self.vt_client:
            return {"source": "virustotal", "score": 0}
        try:
            result = await self.vt_client.scan_domain(domain)
            if result.get("found"):
                return {
                    "source": "virustotal",
                    "score": result.get("threat_score", 0),
                    "tags": result.get("tags", []),
                    "categories": result.get("categories", {}),
                    "last_seen": result.get("last_analysis_date"),
                    "reputation": result.get("reputation", 0),
                    "malicious": result.get("malicious", 0) > result.get("harmless", 0)
                }
        except Exception as e:
            logger.error(f"VT domain lookup failed for {domain}: {e}")
        return {"source": "virustotal", "score": 0}

    async def _lookup_urlhaus(self, url: str) -> Dict[str, Any]:
        """URLhaus URL lookup."""
        if not self.urlhaus_client:
            return {"source": "urlhaus", "score": 0}
        try:
            result = await self.urlhaus_client.lookup_url(url)
            if result.get("found"):
                return {
                    "source": "urlhaus",
                    "score": result.get("threat_score", 85),
                    "tags": result.get("tags", ["malware"]),
                    "threat": result.get("threat", ""),
                    "last_seen": result.get("last_seen")
                }
        except Exception as e:
            logger.error(f"URLhaus lookup failed for {url}: {e}")
        return {"source": "urlhaus", "score": 0}

    async def _lookup_emerging_threats(self, indicator: str, ioc_type: str) -> Dict[str, Any]:
        """Emerging Threats IOC lookup."""
        if not self.et_client:
            return {"source": "emerging_threats", "score": 0}
        try:
            result = await self.et_client.search_ioc(indicator, ioc_type)
            if result.get("found"):
                return {
                    "source": "emerging_threats",
                    "score": result.get("threat_score", 0),
                    "tags": result.get("tags", []),
                    "confidence": result.get("confidence", 0),
                    "malicious": result.get("malicious", False),
                    "last_seen": result.get("last_seen")
                }
        except Exception as e:
            logger.error(f"ET lookup failed for {indicator}: {e}")
        return {"source": "emerging_threats", "score": 0}

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    def _score_to_severity(self, score: int) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        return "low"

    def _is_cached(self, key: str) -> bool:
        if key not in self._cache_timestamps:
            return False
        return datetime.utcnow() - self._cache_timestamps[key] < timedelta(seconds=CACHE_TTL)

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.utcnow()

    def _get_cache(self, key: str) -> Optional[Any]:
        if self._is_cached(key):
            return self._cache.get(key)
        return None

    def _detect_ioc_type(self, indicator: str) -> str:
        """Auto-detect IOC type from value."""
        import re
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", indicator):
            return "ip"
        if re.match(r"^[a-fA-F0-9]{32}$", indicator):
            return "md5"
        if re.match(r"^[a-fA-F0-9]{40}$", indicator):
            return "sha1"
        if re.match(r"^[a-fA-F0-9]{64}$", indicator):
            return "sha256"
        if re.match(r"^https?://", indicator):
            return "url"
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,}$", indicator):
            return "domain"
        return "unknown"

    async def _lookup_internal_db(self, indicator: str, ioc_type: str) -> Dict[str, Any]:
        """Check internal IOC database."""
        if not self.ioc_repo:
            return {"found": False}
        try:
            results = await self.ioc_repo.lookup(indicator, ioc_type)
            if results:
                best = results[0]
                return {
                    "found": True,
                    "ioc_id": best.get("ioc_id"),
                    "threat_score": best.get("threat_score", 0),
                    "severity": best.get("severity", "medium"),
                    "confidence": best.get("confidence", 0),
                    "last_seen": best.get("last_seen"),
                    "seen_count": best.get("seen_count", 1),
                    "source": best.get("source"),
                    "tags": best.get("tags", []),
                    "needs_refresh": best.get("seen_count", 1) == 1  # Refresh new IOCs
                }
        except Exception:
            pass
        return {"found": False}

    async def _persist_ioc(self, indicator: str, ioc_type: str, result: Dict):
        """Persist IOC lookup result to database."""
        if not self.ioc_repo:
            return
        try:
            source = result.get("sources", ["unknown"])[0] if result.get("sources") else "unknown"
            ioc = IOC(
                indicator=indicator,
                ioc_type=ioc_type,
                source=source,
                severity=IOCSeverity.CRITICAL if result["threat_score"] >= 80 else
                         IOCSeverity.HIGH if result["threat_score"] >= 50 else
                         IOCSeverity.MEDIUM if result["threat_score"] >= 30 else IOCSeverity.LOW,
                confidence=result["threat_score"] / 100.0,
                threat_score=result["threat_score"],
                tags=result.get("tags", []),
                metadata={"details": result.get("details", {})}
            )
            await self.ioc_repo.upsert_ioc(ioc)
        except Exception as e:
            logger.debug(f"IOC persistence failed: {e}")

    async def update_cache(self):
        """Background task to refresh and clean cache."""
        now = datetime.utcnow()
        expired = [k for k, v in self._cache_timestamps.items()
                   if now - v >= timedelta(seconds=CACHE_TTL)]
        for k in expired:
            self._cache.pop(k, None)
            self._cache_timestamps.pop(k, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        return {
            "cache_size": len(self._cache),
            "demo_mode": self.demo_mode,
            "air_gapped": self.air_gapped,
            "sources_configured": {
                "otx": bool(self.otx_key),
                "misp": bool(self.misp_url and self.misp_key),
                "virustotal": bool(self.vt_key),
                "abuseipdb": bool(self.abuseipdb_key),
                "urlhaus": bool(self.urlhaus_client),
                "emerging_threats": bool(self.et_client),
                "stix_taxii": self.taxii_enabled,
                "ioc_repository": bool(self.ioc_repo)
            }
        }