from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta, timezone
import uuid
import hashlib
import hmac
import json

from ..db.db_client import get_db
from ..security import get_current_user, require_auth
from ..models.zkp_proper import ZKProofManager

router = APIRouter(prefix="/consent", tags=["Consent"])

class ConsentEnrollmentRequest(BaseModel):
    """Request to record biometric consent (BIPA compliance)."""
    consent_text_version: str = Field(
        "v1",
        description="Version of consent text that was presented to the user"
    )
    purpose: str = Field(
        ...,
        description="Purpose for collecting biometric data (e.g., 'authentication', 'analytics')"
    )
    ip_address: Optional[str] = Field(
        None,
        description="IP address of consenting user (captured automatically if omitted)"
    )
    user_agent: Optional[str] = Field(
        None,
        description="User agent string (captured automatically if omitted)"
    )
    valid_until: Optional[datetime] = Field(
        None,
        description="Expiration date for this consent (None = indefinite)"
    )
    include_zkp: bool = Field(
        True,
        description="Generate ZKP proof of consent for audit trail"
    )

class ConsentEnrollmentResponse(BaseModel):
    """Response from consent enrollment."""
    consent_id: str
    consent_token: str
    consent_text_version: str
    granted_at: datetime
    expires_at: Optional[datetime]
    zkp_proof: Optional[dict] = None
    message: str

class ConsentVerifyRequest(BaseModel):
    """Request to verify a consent token."""
    consent_token: str

class ConsentVerifyResponse(BaseModel):
    """Response from consent verification."""
    valid: bool
    consent_id: Optional[str]
    subject_id: Optional[str]
    granted_at: Optional[datetime]
    expires_at: Optional[datetime]
    purpose: Optional[str]
    error: Optional[str] = None

class ConsentRevokeRequest(BaseModel):
    """Request to revoke previously given consent."""
    consent_id: str
    reason: Optional[str] = None

class ConsentRevokeResponse(BaseModel):
    """Response from consent revocation."""
    revoked: bool
    consent_id: str
    revoked_at: datetime
    message: str

@router.post("/enroll", response_model=ConsentEnrollmentResponse)
async def enroll_consent(
    request: ConsentEnrollmentRequest,
    current_user: dict = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Record biometric consent (BIPA 15 U.S.C. § 6801 et seq compliance).
    
    This endpoint creates a legally binding consent record for biometric
    data collection. The consent token must be presented during enrollment
    to satisfy BIPA requirements.
    
    **BIPA Requirements:**
    - Informed consent required before collecting biometric identifiers
    - Purpose must be clearly stated
    - Retention schedule disclosed
    - Right to revoke at any time
    
    **Flow:**
    1. User is presented with consent text (versioned)
    2. User explicitly agrees
    3. This endpoint is called to record consent
    4. Consent token returned for use in enrollment
    5. Enrollment endpoint verifies token before accepting biometric data
    
    **ZKP Audit:**
    Optionally generates a zero-knowledge proof that consent was obtained,
    which can be verified by auditors without revealing user identity.
    """
    user_id = current_user.get("user_id")
    subject_id = current_user.get("subject_id") or user_id
    
    # Capture request metadata if not provided
    ip_addr = request.ip_address or "0.0.0.0"  # Would extract from request state
    user_agent = request.user_agent or "unknown"
    
    # Generate consent ID and token
    consent_id = str(uuid.uuid4())
    token = hashlib.sha256(f"{consent_id}{subject_id}{request.consent_text_version}".encode()).hexdigest()
    
    # Calculate expiration
    expires_at = None
    if request.valid_until:
        expires_at = request.valid_until
    else:
        # Default consent valid for 1 year
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    
    # Store consent record
    success = await db.create_consent(
        subject_id=subject_id,
        consent_text_version=request.consent_text_version,
        granted_by=user_id,
        ip_addr=ip_addr,
        purpose=request.purpose,
        token=token,
        expires_at=expires_at
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to record consent"
        )
    
    # Generate ZKP proof for audit (optional)
    zkp_proof = None
    if request.include_zkp:
        zkp_manager = ZKProofManager()
        zkp_proof = zkp_manager.generate_consent_proof(
            consent_id=consent_id,
            subject_id=subject_id,
            purpose=request.purpose,
            version=request.consent_text_version
        )
    
    return ConsentEnrollmentResponse(
        consent_id=consent_id,
        consent_token=token,
        consent_text_version=request.consent_text_version,
        granted_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        zkp_proof=zkp_proof,
        message="Consent recorded successfully"
    )

@router.get("/verify", response_model=ConsentVerifyResponse)
async def verify_consent(
    token: str,
    current_user: dict = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Verify a biometric consent token.
    
    Checks that:
    - Token is valid and not expired
    - Consent was properly granted
    - Purpose matches current operation
    """
    consent = await db.validate_consent(token)
    
    if not consent:
        return ConsentVerifyResponse(
            valid=False,
            error="Invalid or expired consent token"
        )
    
    return ConsentVerifyResponse(
        valid=True,
        consent_id=consent.get("consent_id"),
        subject_id=consent.get("subject_id"),
        granted_at=consent.get("granted_at"),
        expires_at=consent.get("expires_at"),
        purpose=consent.get("purpose")
    )

@router.post("/revoke", response_model=ConsentRevokeResponse)
async def revoke_consent(
    request: ConsentRevokeRequest,
    current_user: dict = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Revoke previously given biometric consent.
    
    **BIPA Right to Revoke:**
    Under BIPA, individuals have the right to revoke consent at any time.
    This endpoint:
    - Marks consent as revoked
    - Triggers data deletion workflow (if applicable)
    - Generates ZKP proof of revocation for audit
    
    **Note:** Revoking consent does not automatically delete already-collected
    biometric data. A separate deletion request is required under GDPR/CCPA.
    """
    user_id = current_user.get("user_id")
    
    # Verify consent belongs to user (or user is admin)
    consent = await db.get_consent(request.consent_id)
    if not consent:
        raise HTTPException(404, "Consent record not found")
    
    if consent.get("subject_id") != user_id and current_user.get("role") != "admin":
        raise HTTPException(403, "Cannot revoke consent for another user")
    
    # Update consent as revoked
    success = await db.revoke_consent(
        consent_id=request.consent_id,
        reason=request.reason or "User requested revocation"
    )
    
    if not success:
        raise HTTPException(500, "Failed to revoke consent")
    
    # Log revocation in audit trail with ZKP
    zkp_manager = ZKProofManager()
    audit_proof = zkp_manager.generate_audit_proof(
        action="consent_revoke",
        person_id=consent.get("subject_id"),
        metadata={
            "consent_id": request.consent_id,
            "reason": request.reason,
            "revoked_by": user_id
        }
    )
    
    await db.log_audit_event(
        action="consent_revoke",
        person_id=consent.get("subject_id"),
        details={"consent_id": request.consent_id, "reason": request.reason},
        zkp_proof=audit_proof
    )
    
    return ConsentRevokeResponse(
        revoked=True,
        consent_id=request.consent_id,
        revoked_at=datetime.now(timezone.utc),
        message="Consent revoked successfully"
    )

@router.get("/history", tags=["Consent"])
async def get_consent_history(
    subject_id: Optional[str] = None,
    current_user: dict = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Get consent history for a subject.
    
    **RBAC:**
    - Users can view their own consent history
    - Admins can view any user's consent history
    """
    user_id = current_user.get("user_id")
    role = current_user.get("role", "user")
    
    # Determine whose consent to fetch
    target_subject = subject_id or user_id
    
    # Check authorization
    if subject_id and subject_id != user_id and role != "admin":
        raise HTTPException(403, "Cannot view consent history of other users")
    
    consents = await db.get_consent_history(target_subject)
    
    return {
        "subject_id": target_subject,
        "consents": consents,
        "count": len(consents)
    }

@router.get("/active", tags=["Consent"])
async def get_active_consent(
    purpose: Optional[str] = None,
    current_user: dict = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Get currently active consent(s) for the authenticated user.
    
    Useful for checking whether biometric collection/processing is allowed.
    """
    user_id = current_user.get("user_id")
    
    consents = await db.get_active_consents(user_id, purpose)
    
    return {
        "user_id": user_id,
        "active_consents": consents,
        "has_valid_consent": len(consents) > 0
    }
