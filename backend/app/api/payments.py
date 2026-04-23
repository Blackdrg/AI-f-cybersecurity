from fastapi import APIRouter, HTTPException, Depends, Request, Response
from typing import List, Optional
from ..schemas import PaymentCreate, PaymentResponse
from ..db.db_client import get_db
from ..security import get_current_user
from ..providers import get_payment_provider, PaymentProvider
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/payments/create-session")
async def create_payment_session(
    payment: PaymentCreate, 
    current_user=Depends(get_current_user),
    provider: PaymentProvider = Depends(get_payment_provider)
):
    """Create a checkout session for payment using configured provider."""
    try:
        result = await provider.create_checkout_session(
            user_id=current_user["user_id"],
            plan_id=payment.plan_id,
            amount=payment.amount
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payments/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks for payment confirmation."""
    try:
        body = await request.body()
        # Verify webhook signature in production
        event = request.state.stripe_event if hasattr(request.state, 'stripe_event') else {"type": "unknown", "data": {"object": {}}}
        
        # Simple parsing for demo
        import json
        try:
            event = json.loads(body)
        except:
            event = {"type": "unknown"}

        if event.get('type') == 'checkout.session.completed':
            session = event.get('data', {}).get('object', {})
            user_id = session.get('metadata', {}).get('user_id')
            plan_id = session.get('metadata', {}).get('plan_id')
            
            if user_id and plan_id:
                db = await get_db()
                subscription_id = str(uuid.uuid4())
                await db.create_subscription(subscription_id, user_id, plan_id, "active")

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/payments/history", response_model=List[PaymentResponse])
async def get_payment_history(current_user=Depends(get_current_user)):
    """Get payment history for current user."""
    db = await get_db()
    payments = await db.get_payment_history(current_user["user_id"])

    return [
        PaymentResponse(
            payment_id=p["payment_id"],
            user_id=p["user_id"],
            amount=float(p["amount"]),
            currency=p["currency"],
            status=p["status"],
            stripe_payment_id=p.get("stripe_payment_id"),
            created_at=p["created_at"].isoformat() if hasattr(p["created_at"], 'isoformat') else str(p["created_at"])
        ) for p in payments
    ]

@router.get("/payments/invoice/{payment_id}")
async def generate_invoice(payment_id: str, current_user=Depends(get_current_user)):
    """Generate a PDF invoice for a specific payment."""
    db = await get_db()
    payment = await db.pool.fetchrow("SELECT * FROM payments WHERE payment_id = $1 AND user_id = $2", payment_id, current_user["user_id"])
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Generate PDF (Mocking the byte stream for now)
    # In production, use reportlab or fpdf
    invoice_content = f"""
    LEVI-AI ENTERPRISE INVOICE
    --------------------------
    Invoice ID: {payment_id}
    Date: {payment['created_at']}
    Customer: {current_user['name']}
    Amount: {payment['amount']} {payment['currency']}
    Status: {payment['status']}
    
    Thank you for choosing LEVI-AI!
    """
    
    return Response(
        content=invoice_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{payment_id}.pdf"}
    )
