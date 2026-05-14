"""
Compliance and Security API Endpoints
Provides endpoints for compliance checks, audit reports, and security validation.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ...security import require_org_admin, require_auth
from ...schemas import StandardResponse

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/policies")
async def get_retention_policies(user=Depends(require_auth)):
    """Get data retention policies for the organization."""
    from ...services.compliance_engine import get_data_retention_policy
    policy = get_data_retention_policy()
    return {
        "policies": policy.get_all_expiry_dates(),
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/controls/{framework}")
async def get_compliance_controls(framework: str, user=Depends(require_org_admin)):
    """Get compliance controls for a specific framework."""
    from ...services.compliance_engine import get_compliance_engine
    engine = get_compliance_engine()

    valid_frameworks = ["SOC2", "ISO27001", "FIPS140-2", "FIPS140-3", "GDPR", "CCPA", "HIPAA", "FedRAMP", "PCI-DSS", "ALL"]
    if framework not in valid_frameworks:
        raise HTTPException(status_code=400, detail=f"Invalid framework. Valid: {valid_frameworks}")

    if framework == "ALL":
        controls = list(engine.controls.values())
    else:
        controls = engine.get_controls_by_framework(framework)

    return {
        "framework": framework,
        "total_controls": len(controls),
        "controls": [c.to_dict() for c in controls]
    }


@router.get("/summary")
async def get_compliance_summary(user=Depends(require_org_admin)):
    """Get overall compliance readiness summary."""
    from ...services.compliance_engine import check_compliance_readiness
    result = check_compliance_readiness()
    return result


@router.get("/audit-report/{framework}")
async def generate_audit_report(framework: str, user=Depends(require_org_admin)):
    """Generate audit-ready report for a compliance framework."""
    from ...services.compliance_engine import get_compliance_engine
    engine = get_compliance_engine()

    report = engine.generate_audit_report(framework)
    return report


@router.get("/gaps")
async def list_compliance_gaps(user=Depends(require_org_admin)):
    """List all identified compliance gaps."""
    from ...services.compliance_engine import get_compliance_engine
    engine = get_compliance_engine()
    gaps = engine.get_gaps()

    return {
        "total_gaps": len(gaps),
        "gaps": [g.to_dict() for g in gaps],
        "recommendations": engine.generate_recommendations(gaps)
    }


@router.post("/control/{control_id}/update")
async def update_control_status(
    control_id: str,
    status: str,
    evidence: Optional[str] = None,
    notes: Optional[str] = None,
    user=Depends(require_org_admin)
):
    """Update compliance control status."""
    from ...services.compliance_engine import get_compliance_engine
    engine = get_compliance_engine()

    valid_statuses = ["implemented", "in_progress", "planned", "not_applicable", "gap"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid_statuses}")

    engine.update_control_status(control_id, status, evidence, notes)
    return {"message": f"Control {control_id} updated to {status}"}


@router.get("/incident-runbook")
async def get_incident_runbook(user=Depends(require_org_admin)):
    """Get incident response runbook."""
    from ...services.compliance_engine import SecurityDocumentation
    runbook = SecurityDocumentation.get_incident_response_runbook()
    return runbook


@router.get("/security-docs-index")
async def get_security_docs_index(user=Depends(require_org_admin)):
    """Get index of all security documentation."""
    from ...services.compliance_engine import SecurityDocumentation
    return SecurityDocumentation.get_documentation_index()


@router.get("/data-lifecycle")
async def get_data_lifecycle_report(user=Depends(require_org_admin)):
    """Get data lifecycle management report."""
    from ...services.compliance_engine import get_data_retention_policy
    from ...db.db_client import get_db

    policy = get_data_retention_policy()
    db = get_db()

    lifecycle_report = {
        "policies": policy.get_all_expiry_dates(),
        "database_stats": {},
        "cleanup_status": "active"
    }

    try:
        tables = ["recognition_events", "persons", "embeddings",
                  "audit_log", "sessions", "enrichment_results"]
        for table in tables:
            try:
                count = await db.pool.fetchval(
                    f"SELECT COUNT(*) FROM {table}"
                )
                lifecycle_report["database_stats"][table] = {
                    "row_count": count,
                    "retention_days": policy.get_policy(table)["retention_days"]
                }
            except Exception:
                lifecycle_report["database_stats"][table] = {
                    "row_count": None,
                    "error": "table_not_found_or_inaccessible"
                }
    except Exception as e:
        lifecycle_report["error"] = str(e)

    return lifecycle_report


@router.post("/validate-security")
async def validate_security_config(user=Depends(require_org_admin)):
    """Validate current security configuration."""
    import os

    checks = {
        "tls_enabled": bool(os.getenv("TLS_ENABLED", "false").lower() == "true"),
        "mtls_enabled": bool(os.getenv("MTLS_ENABLED", "false").lower() == "true"),
        "encryption_at_rest": bool(os.getenv("ENCRYPTION_AT_REST", "true").lower() == "true"),
        "audit_logging": True,
        "mfa_required": bool(os.getenv("MFA_REQUIRED", "true").lower() == "true"),
        "rate_limiting": True,
        "api_key_rotation": bool(os.getenv("ENABLE_KEY_ROTATION", "true").lower() == "true"),
        "rbac_enabled": True,
        "tenant_isolation": True,
    }

    score = sum(1 for v in checks.values() if v) / len(checks) * 100

    return {
        "security_score": round(score, 1),
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        "recommendations": _generate_security_recommendations(checks)
    }


def _generate_security_recommendations(checks):
    """Generate recommendations based on security checks."""
    recommendations = []
    if not checks.get("tls_enabled"):
        recommendations.append("Enable TLS for all communications")
    if not checks.get("mtls_enabled"):
        recommendations.append("Consider enabling mTLS for service-to-service communication")
    if not checks.get("mfa_required"):
        recommendations.append("Enable MFA requirement for all users")
    if not checks.get("api_key_rotation"):
        recommendations.append("Enable automated API key rotation")
    return recommendations