"""JWT Revocation API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
import time
from jose import jwt
from typing import Optional
from app.middleware.authentication import get_jwt_revocation_store

router = APIRouter()

@router.post("/api/v1/auth/revoke")
async def revoke_token(
    token: str,
    reason: Optional[str] = None
):
    """
    Revoke the current JWT token.
    """
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False}
        )
        jti = unverified.get("jti")
        exp = unverified.get("exp")
        
        if not jti:
            raise HTTPException(
                status_code=400,
                detail="Token does not contain JTI"
            )
        
        revocation_store = get_jwt_revocation_store()
        await revocation_store.ensure_connected()
        
        success = await revocation_store.revoke_token(jti, exp or int(time.time()) + 3600)
        
        if success:
            return {
                "success": True,
                "message": "Token revoked successfully",
                "jti": jti
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Revocation service unavailable"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid token: {str(e)}"
        )

@router.post("/api/v1/auth/revoke/batch")
async def revoke_tokens_batch(
    tokens: dict
):
    """
    Revoke multiple JWT tokens at once.
    """
    token_list = tokens.get("tokens", [])
    
    if not token_list:
        raise HTTPException(
            status_code=400,
            detail="No tokens provided"
        )
    
    jtis = []
    expiry = int(time.time()) + 3600
    
    for token in token_list:
        try:
            unverified = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
            jti = unverified.get("jti")
            if jti:
                jtis.append(jti)
            exp = unverified.get("exp")
            if exp:
                expiry = exp
        except:
            continue
    
    if not jtis:
        raise HTTPException(
            status_code=400,
            detail="No valid JTIs found in tokens"
        )
    
    revocation_store = get_jwt_revocation_store()
    await revocation_store.ensure_connected()
    
    result = await revocation_store.revoke_token_batch(jtis, expiry)
    
    return result

@router.get("/api/v1/auth/revoked/{jti}")
async def check_revocation(jti: str):
    """
    Check if a specific JWT token has been revoked.
    """
    revocation_store = get_jwt_revocation_store()
    await revocation_store.ensure_connected()
    
    info = await revocation_store.get_revocation_info(jti)
    
    if info:
        return {
            "success": True,
            "revoked": True,
            **info
        }
    else:
        return {
            "success": True,
            "revoked": False,
            "jti": jti
        }
