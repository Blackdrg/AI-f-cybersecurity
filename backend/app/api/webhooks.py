import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from ..errors import ErrorCode

router = APIRouter()

WEBHOOK_SECRET = "whsec_change_me"

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    if not signature:
        return False
    
    # Handle both raw hex and "sha256=" prefix formats
    if signature.startswith("sha256="):
        signature = signature[7:]
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    x_stripe_signature: Optional[str] = Header(None)
):
    """
    Handle Stripe billing webhooks with signature verification.
    """
    payload = await request.body()
    
    # In production, use stripe.Webhook.construct_event
    # For this OS baseline, we show the manual verification pattern
    if not verify_signature(payload, x_stripe_signature, WEBHOOK_SECRET):
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.AUTH_INVALID_TOKEN, "message": "Invalid webhook signature"}
        )
    
    event = json.loads(payload)
    event_type = event.get("type")
    
    if event_type == "checkout.session.completed":
        # Handle successful payment
        pass
    elif event_type == "customer.subscription.deleted":
        # Handle cancellation
        pass
        
    return {"status": "success"}

@router.post("/webhooks/biometric-event")
async def biometric_event_webhook(
    request: Request,
    x_aif_signature: Optional[str] = Header(None)
):
    """
    Outbound webhook schema reference for external integrations.
    Payload Example:
    {
        "event_id": "uuid",
        "type": "MATCH_FOUND",
        "person_id": "uuid",
        "confidence": 0.98,
        "timestamp": "2026-04-29T23:20:00Z"
    }
    """
    payload = await request.body()
    if not verify_signature(payload, x_aif_signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    return {"status": "acknowledged"}
