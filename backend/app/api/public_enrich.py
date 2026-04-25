from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Dict, Any, Optional
import os

# Optional dependency: slowapi may not be installed in dev environments
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    # Provide a no-op limiter that doesn't restrict
    class DummyLimiter:
        def limit(self, rate: str):
            def decorator(func):
                return func
            return decorator
    limiter = DummyLimiter()
    get_remote_address = lambda: "unknown"

from ..schemas import (
    ConsentRequest, ConsentResponse, PublicEnrichRequest, PublicEnrichResponse,
    EnrichResultDetail, AuditLogsResponse, FlagForReviewRequest
)
from ..aggregator import ResultAggregator
from ..redaction import Redactor
from ..db.db_client import get_db
from ..security import require_auth
from ..metrics import enrichment_requests, enrichment_latency
import time

router = APIRouter()

aggregator = ResultAggregator()
redactor = Redactor()


@router.post("/consent", response_model=ConsentResponse)
@limiter.limit("10/minute")
async def create_consent(
    request: ConsentRequest,
    req: Request,
    user: dict = Depends(require_auth)
):
    """Create consent for public enrichment."""
    db = await get_db()

    # Read consent text
    consent_file = f"docs/consent_texts/{request.consent_text_version}.txt"
    if not os.path.exists(consent_file):
        raise HTTPException(status_code=400, detail="Invalid consent version")

    with open(consent_file, 'r') as f:
        consent_text = f.read()

    # Create consent record
    consent_data = await db.create_consent(
        subject_id=request.subject_id,
        consent_text_version=request.consent_text_version,
        granted_by=user.get("sub", "unknown"),
        ip_addr=req.client.host,
        purpose=request.purpose
    )

    return ConsentResponse(
        consent_id=consent_data["consent_id"],
        token=consent_data["token"],
        expires_at=consent_data["expires_at"],
        message="Consent granted successfully"
    )


@router.post("/public_enrich", response_model=PublicEnrichResponse)
@limiter.limit("5/minute")
async def public_enrich(
    request: PublicEnrichRequest,
    user: dict = Depends(require_auth)
):
    """Perform public enrichment search."""
    start_time = time.time()

    # Validate consent if token provided
    if request.consent_token:
        db = await get_db()
        consent = await db.validate_consent(request.consent_token)
        if not consent:
            raise HTTPException(
                status_code=403, detail="Invalid or expired consent token")

    # Build query from identifiers
    query_parts = []
    if "name" in request.identifiers:
        query_parts.append(request.identifiers["name"])
    if "organization" in request.identifiers:
        query_parts.append(request.identifiers["organization"])
    query = " ".join(query_parts)

    if not query.strip():
        raise HTTPException(
            status_code=400, detail="Insufficient identifiers for search")

    # Perform enrichment
    try:
        results, provider_calls = await aggregator.enrich(
            query=query,
            providers=request.providers,
            limit=10
        )

        # Apply additional redaction
        results = redactor.redact_results(results)

        # Save results to database
        db = await get_db()
        enrich_id = await db.save_enrichment_result(
            query=query,
            subject=str(request.identifiers),
            summary=results,
            requested_by=request.requested_by,
            purpose=request.purpose
        )

        # Log audit
        await db.log_audit(
            action="public_enrich",
            user_id=request.requested_by,
            target_enrich_id=enrich_id,
            provider_calls=provider_calls,
            metadata={
                "providers": request.providers,
                "identifiers": request.identifiers,
                "consent_used": bool(request.consent_token)
            }
        )

        enrichment_requests.inc()
        enrichment_latency.observe(time.time() - start_time)

        return PublicEnrichResponse(
            enrich_id=enrich_id,
            results=results,
            created_at=str(time.time()),
            expires_at=str(time.time() + (7 * 24 * 3600))  # 7 days
        )

    except Exception as e:
        # Log error
        db = await get_db()
        await db.log_audit(
            action="public_enrich_error",
            user_id=request.requested_by,
            provider_calls=[],
            metadata={"error": str(e), "query": query}
        )
        raise HTTPException(status_code=500, detail="Enrichment failed")


@router.get("/public_enrich/{enrich_id}", response_model=EnrichResultDetail)
async def get_enrichment_result(
    enrich_id: str,
    user: dict = Depends(require_auth)
):
    """Get enrichment result by ID."""
    db = await get_db()
    result = await db.get_enrichment_result(enrich_id)

    if not result:
        raise HTTPException(
            status_code=404, detail="Result not found or expired")

    return EnrichResultDetail(
        enrich_id=result["enrich_id"],
        query=result["query"],
        subject=result["subject"],
        summary=result["summary"],
        created_at=result["created_at"].isoformat(),
        expires_at=result["expires_at"].isoformat(),
        requested_by=result["requested_by"],
        purpose=result["purpose"]
    )


@router.get("/audit_logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    user_id: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_auth)
):
    """Get audit logs (admin only)."""
    # In production, check for admin role
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = await get_db()
    logs = await db.get_audit_logs(user_id=user_id, limit=limit)

    return AuditLogsResponse(
        logs=[{
            "audit_id": log["audit_id"],
            "action": log["action"],
            "user_id": log["user_id"],
            "target_enrich_id": log["target_enrich_id"],
            "provider_calls": log["provider_calls"],
            "metadata": log["metadata"],
            "created_at": log["created_at"].isoformat()
        } for log in logs],
        total=len(logs)
    )


@router.post("/flag_for_review")
async def flag_for_review(
    enrich_id: str,
    request: FlagForReviewRequest,
    user: dict = Depends(require_auth)
):
    """Flag enrichment result for review."""
    db = await get_db()

    # Check if result exists
    result = await db.get_enrichment_result(enrich_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    success = await db.flag_for_review(enrich_id, request.reason)

    if success:
        return {"message": "Result flagged for review"}
    else:
        raise HTTPException(status_code=500, detail="Failed to flag result")
