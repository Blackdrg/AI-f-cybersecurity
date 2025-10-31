from fastapi import APIRouter, HTTPException, Depends
from ..schemas import PaymentCreate, PaymentResponse
from ..db.db_client import get_db
from ..security import get_current_user
import stripe
import os
from datetime import datetime
import uuid

router = APIRouter()

# Initialize Stripe
# Use environment variable
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")


@router.post("/payments/create-session")
async def create_payment_session(payment: PaymentCreate, current_user=Depends(get_current_user)):
    """Create a Stripe checkout session for payment."""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Subscription - {payment.plan_id}',
                    },
                    # Convert to cents
                    'unit_amount': int(payment.amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/cancel",
            metadata={
                'user_id': current_user["user_id"],
                'plan_id': payment.plan_id
            }
        )
        return {"session_id": session.id, "url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payments/webhook")
async def stripe_webhook(request: dict):
    """Handle Stripe webhooks for payment confirmation."""
    # Verify webhook signature (implementation depends on your setup)
    event = request

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']
        plan_id = session['metadata']['plan_id']

        # Update user's subscription in database
        # This would typically be handled by a background task
        # For now, we'll just log it
        print(f"Payment completed for user {user_id}, plan {plan_id}")

    return {"status": "success"}


@router.get("/payments/history", response_model=list[PaymentResponse])
async def get_payment_history(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get payment history for current user."""
    query = "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC"
    rows = await db.fetch_all(query, (current_user["user_id"],))

    return [
        PaymentResponse(
            payment_id=row["payment_id"],
            user_id=row["user_id"],
            amount=row["amount"],
            currency=row["currency"],
            status=row["status"],
            stripe_payment_id=row["stripe_payment_id"],
            created_at=row["created_at"]
        ) for row in rows
    ]
