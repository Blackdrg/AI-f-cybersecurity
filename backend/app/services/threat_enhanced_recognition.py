"""
Enhancers for Recognition Events
Applies threat intelligence enrichment to recognition events.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def enrich_recognition_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a recognition event with threat intelligence data.

    Adds threat scores, IOC matches, and risk assessment to events.

    Args:
        event: Recognition event dict with IP, camera_id, person_id fields

    Returns:
        Event dict enriched with threat intelligence
    """
    from app.services.threat_enrichment_pipeline import get_enrichment_pipeline, ThreatEnrichmentPipeline

    pipeline = get_enrichment_pipeline()
    await pipeline.initialize()

    enriched = {**event}
    enriched["enrichment"] = {}
    enriched["threat_flags"] = []

    ioc_sources = []

    # Extract IOCs from event
    if event.get("client_ip"):
        ioc_sources.append((event["client_ip"], "ip"))

    if event.get("camera_ip"):
        ioc_sources.append((event["camera_ip"], "ip"))

    if event.get("device_id"):
        # Check if device ID appears in known malicious indicators
        ioc_sources.append((event["device_id"], "unknown"))

    if event.get("metadata"):
        metadata = event["metadata"]
        if metadata.get("url"):
            ioc_sources.append((metadata["url"], "url"))
        if metadata.get("user_agent"):
            # User agent strings aren't typical IOCs but can be checked
            pass

    if event.get("person_id") and event["person_id"] is None:
        # Unknown person - check if associated IPs are flagged
        pass

    # Enrich each IOC
    threat_scores = []
    for ioc_value, ioc_type in ioc_sources:
        try:
            result = await pipeline.enrich_ioc(ioc_value, ioc_type)
            if result.get("threat_score", 0) > 0:
                enriched["threat_flags"].append({
                    "indicator": ioc_value,
                    "type": ioc_type,
                    "threat_score": result["threat_score"],
                    "malicious": result.get("malicious", False),
                    "sources": result.get("sources", []),
                    "tags": result.get("tags", []),
                })
                threat_scores.append(result["threat_score"])
        except Exception as e:
            logger.warning(f"IOC enrichment failed for {ioc_value}: {e}")

    # Calculate composite threat score
    if threat_scores:
        max_score = max(threat_scores)
        avg_score = sum(threat_scores) / len(threat_scores)
    else:
        max_score = 0
        avg_score = 0

    enriched["threat_assessment"] = {
        "max_threat_score": max_score,
        "avg_threat_score": avg_score,
        "ioc_matches": len(enriched["threat_flags"]),
        "risk_level": _classify_risk(max_score),
        "assessed_at": datetime.utcnow().isoformat(),
    }

    # Add recommended actions
    if max_score >= 80:
        enriched["recommended_actions"] = ["BLOCK", "ALERT_ADMIN", "QUARANTINE"]
    elif max_score >= 50:
        enriched["recommended_actions"] = ["FLAG_FOR_REVIEW", "ALERT_ADMIN"]
    elif max_score >= 30:
        enriched["recommended_actions"] = ["FLAG_FOR_REVIEW"]
    else:
        enriched["recommended_actions"] = []

    return enriched


async def bulk_enrich_events(events: List[Dict]) -> List[Dict]:
    """Enrich multiple recognition events in parallel."""
    tasks = [enrich_recognition_event(event) for event in events]
    return await asyncio.gather(*tasks, return_exceptions=True)


def _classify_risk(score: int) -> str:
    """Classify risk level based on threat score."""
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "low"
    else:
        return "minimal"


async def trigger_threat_workflow(event: Dict, threat_score: int,
                                   matched_iocs: List[Dict]) -> Optional[str]:
    """
    Trigger an appropriate threat response workflow.

    Returns incident_id if a workflow was triggered, None otherwise.
    """
    from app.services.incident_response import incident_engine

    incident_event = {
        "event_type": "threat_intel_match",
        "person_id": event.get("person_id"),
        "camera_id": event.get("camera_id"),
        "confidence": threat_score / 100.0,
        "threat_score": threat_score,
        "ioc_count": len(matched_iocs),
        "matched_iocs": matched_iocs,
        "ip": event.get("client_ip"),
        "timestamp": event.get("timestamp"),
        "org_id": event.get("org_id"),
    }

    severity = "medium"
    if threat_score >= 80:
        severity = "critical"
        incident_event["count"] = 5  # Force rule matching
    elif threat_score >= 50:
        severity = "high"
        incident_event["count"] = 5

    incident_event["threat_score"] = threat_score
    incident_event["severity"] = severity

    incident = await incident_engine.evaluate_event(incident_event)
    if incident:
        logger.info(f"Threat workflow triggered: {incident.incident_id}")
        return incident.incident_id

    return None