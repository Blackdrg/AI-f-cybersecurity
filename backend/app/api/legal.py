from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..schemas import ConsentRequest, ConsentResponse
from ..db.db_client import get_db
from ..security import get_current_user
from ..legal_compliance import legal_compliance, Region, Purpose, BiometricType
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/consent", response_model=ConsentResponse)
async def create_consent(
    request: ConsentRequest,
    current_user=Depends(get_current_user)
):
    """Create consent record for biometric processing."""
    region = Region(request.get("region", "us"))
    
    record = legal_compliance.record_consent(
        user_id=current_user["user_id"],
        purpose=Purpose.AUTHENTICATION,
        biometric_types=[BiometricType.FACE],
        region=region,
        granted=request.get("granted", True)
    )
    
    return ConsentResponse(
        consent_id=record.consent_id,
        token=record.consent_id,
        expires_at=record.expires_at,
        message="Consent recorded successfully"
    )


@router.delete("/consent/{consent_id}")
async def withdraw_consent(
    consent_id: str,
    current_user=Depends(get_current_user)
):
    """Withdraw consent."""
    success = legal_compliance.withdraw_consent(consent_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Consent not found")
    
    return {"message": "Consent withdrawn successfully"}


@router.get("/compliance/features")
async def get_available_features(
    region: str = "us"
):
    """Get available features for region."""
    r = Region(region)
    features = legal_compliance.get_available_features(r)
    
    return {
        "region": r.value,
        "features": features
    }


@router.get("/compliance/audit")
async def get_audit_trail(
    current_user=Depends(get_current_user),
    limit: int = 50
):
    """Get user's audit trail."""
    logs = legal_compliance.get_audit_trail(
        user_id=current_user["user_id"],
        limit=limit
    )
    
    return {"logs": logs, "total": len(logs)}


@router.get("/compliance/data-subject")
async def get_data_subject_access(
    current_user=Depends(get_current_user)
):
    """Generate data subject access request response."""
    data = legal_compliance.generate_data_subject_access(
        current_user["user_id"]
    )
    
    return data


@router.post("/compliance/delete")
async def request_deletion(
    current_user=Depends(get_current_user)
):
    """Request data deletion (GDPR art 17)."""
    request = legal_compliance.generate_deletion_request(
        current_user["user_id"]
    )
    
    return request


@router.get("/compliance/impact-assessment")
async def get_impact_assessment(
    region: str = "us",
    purpose: str = "authentication",
    data_scale: int = 1000
):
    """Get DPIA/impact assessment."""
    r = Region(region)
    p = Purpose(purpose)
    
    assessment = legal_compliance.generate_impact_assessment(
        r, p, data_scale
    )
    
    return assessment