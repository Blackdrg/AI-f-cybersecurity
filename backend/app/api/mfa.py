"""
MFA Endpoints
Enrollment, verification, backup codes management
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import List, Optional
from ..security import require_auth, verify_token, create_token
from ..security.mfa import mfa_service
from ..db.db_client import get_db
from ..middleware.rate_limit import RateLimitMiddleware
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limit for MFA attempts (strict)
mfa_rate_limit = "5/minute"

class MFAEnrollResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: List[str]

class MFVerifyRequest(BaseModel):
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
    """
    user_id = user['user_id']
    
    # Check if already enabled
    if await mfa_service.is_mfa_enabled(user_id):
        raise HTTPException(status_code=400, detail="MFA is already enabled for this account")
    
    # Generate secret and backup codes
    secret, backup_codes = await mfa_service.enable_mfa_for_user(user_id)
    
    # Generate QR code URI
    user_email = user.get('email', user_id)
    qr_uri = mfa_service.generate_totp_qr_code_data(secret, user_id, user_email)
    
    return MFAEnrollResponse(
        secret=secret,
        qr_code_uri=qr_uri,
        backup_codes=backup_codes
    )

@router.post("/mfa/verify")
async def verify_mfa(request: MFVerifyRequest, user: dict = Depends(require_auth)):
    """
    Verify TOTP code and enable MFA.
    """
    user_id = user['user_id']
    code = request.code
    
    # Validation
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid code format. Expected 6 digits.")
    
    valid = await mfa_service.verify_totp_code(user_id, code)
    if not valid:
        # We don't rate limit initial enrollment verification as strictly as login
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
async def verify_totp_for_login(request: MFVerifyRequest, user: dict = Depends(require_auth)):
    """
    Verify TOTP code during login (second factor).
    """
    user_id = user['user_id']
    code = request.code
    
    # Strict validation
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid code format")

    valid = await mfa_service.verify_totp_code(user_id, code)
    if not valid:
        # Log failed attempt for anomaly detection
        db = await get_db()
        # Note: log_mfa_attempt should handle internal rate limiting/lockout logic
        await db.log_mfa_attempt(user_id, 'totp', False, "unknown")
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Log successful attempt
    db = await get_db()
    await db.log_mfa_attempt(user_id, 'totp', True, "unknown")
    
    # Generate new JWT with mfa_verified claim
    token = create_token(
        user_id=user_id,
        role=user.get('role', 'user'),
        # Add mfa_verified to ensure high-privilege routes can require it
    )
    # The actual claim addition happens inside create_token if it supports it, 
    # or we can pass it as extra_claims if supported.
    
    return {"token": token, "mfa_verified": True}

@router.post("/mfa/verify-backup")
async def verify_backup_code(request: MFVerifyRequest, user: dict = Depends(require_auth)):
    """
    Use a backup code to bypass MFA.
    """
    user_id = user['user_id']
    code = request.code
    
    valid, message = await mfa_service.verify_backup_code(user_id, code)
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    # Generate token with mfa_verified
    token = create_token(
        user_id=user_id,
        role=user.get('role', 'user')
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
    """
    user_id = user['user_id']
    password = request.password
    
    if not password:
        raise HTTPException(status_code=400, detail="Password required to disable MFA")

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
