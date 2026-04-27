"""
MFA Endpoints
Enrollment, verification, backup codes management
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import List, Optional
from ..security import require_auth, verify_token
from ..security.mfa import mfa_service
from ..db.db_client import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class MFAEnrollResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: List[str]


class MFverifyRequest(BaseModel):
    code: str


class MFAVerifyResponse(BaseModel):
    verified: bool
    message: str


class MFAEnableRequest(BaseModel):
    password: str


@router.post("/mfa/enroll")
async def enroll_mfa(user: dict = Depends(require_auth)):
    """
    Start MFA enrollment.
    
    Generates TOTP secret and backup codes.
    Returns secret for app setup and QR code URI.
    Client should generate QR code from the URI.
    """
    user_id = user['user_id']
    
    # Generate secret and backup codes
    secret, backup_codes = await mfa_service.enable_mfa_for_user(user_id)
    
    # Generate QR code URI
    user_email = user.get('email', user_id)
    qr_uri = mfa_service.generate_totp_qr_code_data(secret, user_id, user_email)
    
    # Store in DB (pending verification)
    # The secret is stored but MFA not yet enabled until verified
    
    return MFAEnrollResponse(
        secret=secret,
        qr_code_uri=qr_uri,
        backup_codes=backup_codes
    )


@router.post("/mfa/verify")
async def verify_mfa(request: MFverifyRequest, user: dict = Depends(require_auth)):
    """
    Verify TOTP code and enable MFA.
    
    User scans QR code into authenticator app, then enters code here
    to confirm setup.
    """
    user_id = user['user_id']
    code = request.code
    
    valid = await mfa_service.verify_totp_code(user_id, code)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # Enable MFA for user
    await mfa_service.enable_mfa_after_verification(user_id)
    
    # Log audit event
    db = await get_db()
    await db.log_audit_event(
        action="mfa_enabled",
        person_id=None,
        details={"user_id": user_id, "method": "totp"}
    )
    
    return {"verified": True, "message": "MFA enabled successfully"}


@router.post("/mfa/verify-totp")
async def verify_totp_for_login(request: MFverifyRequest, user: dict = Depends(require_auth)):
    """
    Verify TOTP code during login (second factor).
    Returns a new JWT token with 'mfa_verified' claim.
    """
    user_id = user['user_id']
    code = request.code
    
    valid = await mfa_service.verify_totp_code(user_id, code)
    if not valid:
        # Log failed attempt
        db = await get_db()
        await db.log_mfa_attempt(user_id, 'totp', False, request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Log successful attempt
    db = await get_db()
    await db.log_mfa_attempt(user_id, 'totp', True, request.client.host if request.client else None)
    
    # Generate new JWT with mfa_verified claim
    token = create_token(
        user_id=user_id,
        role=user.get('role', 'user'),
        extra_claims={'mfa_verified': True}
    )
    
    return {"token": token, "mfa_verified": True}


@router.post("/mfa/verify-backup")
async def verify_backup_code(request: MFverifyRequest, user: dict = Depends(require_auth)):
    """
    Use a backup code to bypass MFA (consumes the code).
    Returns a new JWT token.
    """
    user_id = user['user_id']
    code = request.code
    
    valid, message = await mfa_service.verify_backup_code(user_id, code)
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    # Generate token with mfa_verified
    token = create_token(
        user_id=user_id,
        role=user.get('role', 'user'),
        extra_claims={'mfa_verified': True, 'used_backup_code': True}
    )
    
    # Log
    db = await get_db()
    await db.log_audit_event(
        action="mfa_backup_used",
        person_id=None,
        details={"user_id": user_id}
    )
    
    return {"token": token, "used_backup": True}


@router.get("/mfa/status")
async def mfa_status(user: dict = Depends(require_auth)):
    """Check if MFA is enabled for current user"""
    user_id = user['user_id']
    enabled = await mfa_service.is_mfa_enabled(user_id)
    backup_codes_remaining = await mfa_service.get_backup_codes_count(user_id)
    return {"enabled": enabled, "backup_codes_remaining": backup_codes_remaining}


@router.post("/mfa/disable")
async def disable_mfa(request: MFAEnableRequest, user: dict = Depends(require_auth)):
    """
    Disable MFA for the current user.
    Requires password confirmation.
    """
    user_id = user['user_id']
    password = request.password
    
    success = await mfa_service.disable_mfa(user_id, password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid password")
    
    # Log
    db = await get_db()
    await db.log_audit_event(
        action="mfa_disabled",
        person_id=None,
        details={"user_id": user_id}
    )
    
    return {"disabled": True, "message": "MFA disabled"}


@router.get("/mfa/backup-codes/remaining")
async def get_remaining_backup_codes(user: dict = Depends(require_auth)):
    """Get count of remaining backup codes"""
    user_id = user['user_id']
    count = await mfa_service.get_backup_codes_count(user_id)
    return {"remaining": count}
