"""
Threat Enrichment Pipeline
Enriches recognition events and incidents with threat intelligence data.
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.threat_cache import ThreatIntelCache
from app.schemas import IOCEnrichmentRequest

logger = logging.getLogger(__name__)

try:
    from app.providers.virustotal_provider import VirusTotalProvider
    VT_AVAILABLE = True
except ImportError:
    VT_AVAILABLE = False

try:
    from app.providers.urlhaus_provider import URLhausProvider
    URLHAUS_AVAILABLE = True
except ImportError:
    URLHAUS_AVAILABLE = False

try:
    from app.providers.emerging_threats_provider import EmergingThreatsProvider
    ET_AVAILABLE = True
except ImportError:
    ET_AVAILABLE = False

try:
    from app.providers.threat_intel_provider import ThreatIntelProvider
    TI_AVAILABLE = True
except ImportError:
    TI_AVAILABLE = False

try:
    from app.providers.stix_taxii_provider import STIXTaxiiClient
    STIX_AVAILABLE = True
except ImportError:
    STIX_AVAILABLE = False


class ThreatEnrichmentPipeline:
    """Pipeline for enriching events with threat intelligence."""

    def __init__(self):
        self.cache = ThreatIntelCache()
        self.ti_provider = ThreatIntelProvider() if TI_AVAILABLE else None
        self.vt_provider = VirusTotalProvider() if VT_AVAILABLE else None
        self.urlhaus_provider = URLhausProvider() if URLHAUS_AVAILABLE else None
        self.et_provider = EmergingThreatsProvider() if ET_AVAILABLE else None
        self._initialized = False

    async def initialize(self):
        """Initialize all providers and caching layer."""
        if self._initialized:
            return
        await self.cache.connect()
        self._initialized = True

    async def shutdown(self):
        """Shutdown all providers and connections."""
        await self.cache.disconnect()
        if self.vt_provider:
            await self.vt_provider.close()
        if self.urlhaus_provider:
            await self.urlhaus_provider.close()
        if self.et_provider:
            await self.et_provider.close()

    async def enrich_ioc(self, ioc_value: str, ioc_type: str = "auto",
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Enrich an IOC through all available providers with caching.

        Args:
            ioc_value: The indicator value
            ioc_type: Type of IOC (auto, ip, domain, url, hash, email)
            force_refresh: Force fresh lookup, bypass cache

        Returns:
            Enrichment result with combined scores and sources
        """
        if not force_refresh:
            cached = await self.cache.get_ioc(ioc_value, ioc_type)
            if cached is not None:
                cached["_cached"] = True
                return cached

        # Auto-detect IOC type if not specified
        if ioc_type == "auto":
            ioc_type = self._detect_type(ioc_value)

        # Gather enrichment from all available providers
        tasks = []

        # Try in-memory TI provider (OTX, MISP, AbuseIPDB)
        if self.ti_provider:
            try:
                tasks.append(self._safe_lookup_ti(self.ti_provider, ioc_value, ioc_type))
            except Exception:
                pass

        # Try VirusTotal for hashes, URLs, domains
        if self.vt_provider and self.vt_provider.is_configured():
            if ioc_type in ("hash", "url", "domain"):
                try:
                    tasks.append(self._safe_lookup_vt(ioc_value, ioc_type))
                except Exception:
                    pass

        # Try URLhaus for URLs
        if self.urlhaus_provider and self.urlhaus_provider.is_configured():
            if ioc_type in ("url", "domain"):
                try:
                    tasks.append(self._safe_lookup_urlhaus(ioc_value))
                except Exception:
                    pass

        # Try Emerging Threats
        if self.et_provider and self.et_provider.is_configured():
            try:
                tasks.append(self._safe_lookup_et(ioc_value, ioc_type))
            except Exception:
                pass

        # Execute all lookups in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        enrichment = self._aggregate_results(ioc_value, ioc_type, results)

        # Cache the result
        await self.cache.set_ioc(ioc_value, ioc_type, enrichment)

        return enrichment

    async def enrich_receipt_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a full recognition event with threat intel."""
        await self.initialize()

        enriched_event = event.copy()
        enriched_event["enrichment"] = {}
        enriched_event["threat_intel"] = []
        enriched_event["enrichment_timestamp"] = datetime.utcnow().isoformat()

        # Sources of IOCs to check
        ioc_sources = []

        # Check IP from event metadata
        client_ip = event.get("client_ip")
        if client_ip:
            ioc_sources.append((client_ip, "ip"))

        # Check for any URLs in event data
        event_data = event.get("data", {})
        if isinstance(event_data, dict):
            if "request_url" in event_data:
                ioc_sources.append((event_data["request_url"], "url"))
            if "referer" in event_data:
                ioc_sources.append((event_data["referer"], "url"))

        # Enrich each IOC
        threat_score = 0
        threat_sources = []
        for ioc_value, ioc_type in ioc_sources:
            try:
                result = await self.enrich_ioc(ioc_value, ioc_type)
                enriched_event["threat_intel"].append(result)

                if result.get("threat_score", 0) > threat_score:
                    threat_score = result["threat_score"]
                    threat_sources = result.get("sources", [])

                if result.get("malicious", False):
                    enriched_event["flags"] = enriched_event.get("flags", []) + ["THREAT_INTEL_MATCH"]
            except Exception as e:
                logger.warning(f"Enrichment failed for {ioc_value}: {e}")

        # Set overall threat score on event
        enriched_event["threat_score"] = threat_score
        enriched_event["threat_sources"] = threat_sources

        # Log enrichment to audit trail
        enriched_event["enrichment"] = {
            "sources_checked": len(enriched_event["threat_intel"]),
            "highest_threat_score": threat_score,
            "cached": any(r.get("_cached", False) for r in enriched_event["threat_intel"]),
            "enrichment_time_ms": 0  # Populated by caller
        }

        return enriched_event

    def _detect_type(self, value: str) -> str:
        """Auto-detect IOC type."""
        import re
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
            return "ip"
        if re.match(r"^[a-fA-F0-9]{32}$", value):
            return "md5"
        if re.match(r"^[a-fA-F0-9]{40}$", value):
            return "sha1"
        if re.match(r"^[a-fA-F0-9]{64}$", value):
            return "sha256"
        if re.match(r"^https?://", value):
            return "url"
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,}$", value):
            return "domain"
        if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            return "email"
        return "unknown"

    # ──────────────────────────────────────────
    # Private Helper Methods
    # ──────────────────────────────────────────

    async def _safe_lookup_ti(self, provider, ioc_value, ioc_type):
        """Safely call threat intel provider."""
        try:
            result = await provider.lookup_ioc(ioc_value, ioc_type)
            result["provider"] = provider.__class__.__name__
            return result
        except Exception as e:
            logger.error(f"TI provider lookup failed: {e}")
            return {"error": str(e), "provider": provider.__class__.__name__}

    async def _safe_lookup_vt(self, ioc_value, ioc_type):
        """Safely call VirusTotal provider."""
        try:
            if ioc_type == "hash":
                result = await self.vt_provider.lookup_file_hash(ioc_value)
            elif ioc_type == "url":
                result = await self.vt_provider.lookup_url_report(ioc_value)
            else:
                result = await self.vt_provider.scan_domain(ioc_value)
            result["provider"] = "virustotal"
            return result
        except Exception as e:
            logger.error(f"VirusTotal lookup failed: {e}")
            return {"error": str(e), "provider": "virustotal"}

    async def _safe_lookup_urlhaus(self, ioc_value):
        """Safely call URLhaus provider."""
        try:
            result = await self.urlhaus_provider.lookup_url(ioc_value)
            result["provider"] = "urlhaus"
            return result
        except Exception as e:
            logger.error(f"URLhaus lookup failed: {e}")
            return {"error": str(e), "provider": "urlhaus"}

    async def _safe_lookup_et(self, ioc_value, ioc_type):
        """Safely call Emerging Threats provider."""
        try:
            result = await self.et_provider.search_ioc(ioc_value, ioc_type)
            result["provider"] = "emerging_threats"
            return result
        except Exception as e:
            logger.error(f"Emerging Threats lookup failed: {e}")
            return {"error": str(e), "provider": "emerging_threats"}

    def _aggregate_results(self, ioc_value: str, ioc_type: str,
                           results: List[Any]) -> Dict[str, Any]:
        """Aggregate results from multiple providers."""
        aggregated = {
            "indicator": ioc_value,
            "ioc_type": ioc_type,
            "sources": [],
            "confidence": 0,
            "threat_score": 0,
            "malicious": False,
            "first_seen": None,
            "last_seen": None,
            "tags": [],
            "enrichment_time": datetime.utcnow().isoformat()
        }

        max_score = 0
        all_tags = []
        malicious_count = 0

        for result in results:
            if isinstance(result, Exception):
                aggregated["sources"].append({"error": str(result)})
                continue

            provider_name = result.get("provider", "unknown")
            score = result.get("threat_score", 0) or result.get("confidence", 0)

            aggregated["sources"].append({
                "provider": provider_name,
                "score": score,
                "found": result.get("found", True),
                "details": result
            })

            if score > max_score:
                max_score = score

            # Count malicious results
            if result.get("malicious", False):
                malicious_count += 1

            # Collect tags
            all_tags.extend(result.get("tags", []))

            # Track dates
            first = result.get("first_seen")
            last = result.get("last_seen")
            if first:
                aggregated["first_seen"] = first
            if last:
                aggregated["last_seen"] = last

        aggregated["threat_score"] = max_score
        aggregated["malicious"] = malicious_count > 0
        aggregated["confidence"] = max_score / 100.0
        aggregated["tags"] = list(set(all_tags))

        return aggregated


# Global singleton instance
_enrichment_pipeline: Optional[ThreatEnrichmentPipeline] = None


def get_enrichment_pipeline() -> ThreatEnrichmentPipeline:
    """Get or create global enrichment pipeline instance."""
    global _enrichment_pipeline
    if _enrichment_pipeline is None:
        _enrichment_pipeline = ThreatEnrichmentPipeline()
    return _enrichment_pipeline