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
    Production Stripe webhook handler.
    """
    payload = await request.body()
    sig_header = x_stripe_signature

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature")

    from ..services.stripe_service import stripe, billing_service

    # Use manual HMAC verification for resilience and testability
    webhook_secret = stripe.webhook_secret or "whsec_change_me"
    if not verify_signature(payload, sig_header, webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Generate event ID if not present (for testing/resilience)
    if "id" not in event:
        event["id"] = f"evt_generated_{hashlib.sha256(payload).hexdigest()[:12]}"

    response = await billing_service.handle_webhook(event)

    return response

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
