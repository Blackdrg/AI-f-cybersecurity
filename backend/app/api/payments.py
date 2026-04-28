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
    """
    Handle Stripe webhooks for payment events.
    
    Secured by verifying webhook signature (STRIPE_WEBHOOK_SECRET).
    Handles multiple event types with idempotency.
    """
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    if not signature:
        logger.warning("Webhook called without Stripe signature")
        return {"status": "error", "detail": "Missing signature"}, 400
    
    # Verify webhook signature (CRITICAL for security)
    try:
        import stripe
        event = stripe.Webhook.construct_event(
            body, signature, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        return {"status": "error", "detail": "Invalid payload"}, 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        return {"status": "error", "detail": "Invalid signature"}, 400
    
    db = await get_db()
    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})
    
    logger.info(f"Processing Stripe webhook: {event_type}")
    
    try:
        # Handle different event types
        if event_type == "checkout.session.completed":
            # Payment successful — activate subscription
            session = event_data
            user_id = session.get("metadata", {}).get("user_id")
            plan_id = session.get("metadata", {}).get("plan_id")
            subscription_id = session.get("subscription")
            
            if user_id and plan_id and subscription_id:
                await db.create_subscription(
                    subscription_id=subscription_id,
                    user_id=user_id,
                    plan_id=plan_id,
                    status="active",
                    starts_at=session.get("created"),
                    ends_at=session.get("current_period_end")
                )
                
                # Log successful payment
                await db.log_payment(
                    user_id=user_id,
                    amount=session.get("amount_total", 0) / 100,  # cents to dollars
                    currency=session.get("currency", "usd").upper(),
                    status="succeeded",
                    stripe_payment_id=session.get("payment_intent"),
                    metadata={"event": "checkout.session.completed"}
                )
        
        elif event_type == "invoice.payment_failed":
            # Payment failed — downgrade user to free tier, notify
            invoice = event_data
            subscription_id = invoice.get("subscription")
            customer_id = invoice.get("customer")
            
            # Look up user by Stripe customer ID
            user = await db.get_user_by_stripe_customer(customer_id)
            if user:
                await db.downgrade_to_free_tier(user["user_id"])
                
                # Send notification email (async task)
                from app.tasks.maintenance_tasks import send_payment_failed_email
                send_payment_failed_email.delay(user["email"], invoice.get("amount_due", 0))
                
                logger.warning(f"Payment failed for user {user['user_id']} — downgraded to free")
        
        elif event_type == "customer.subscription.deleted":
            # Subscription cancelled (by user or Stripe)
            subscription = event_data
            stripe_customer_id = subscription.get("customer")
            
            user = await db.get_user_by_stripe_customer(stripe_customer_id)
            if user:
                # Mark subscription inactive
                await db.deactivate_subscription(user["user_id"])
                logger.info(f"Subscription ended for user {user['user_id']}")
        
        elif event_type == "customer.subscription.updated":
            # Subscription updated (plan change, renewal, etc.)
            subscription = event_data
            stripe_customer_id = subscription.get("customer")
            new_plan = subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("lookup_key")
            
            user = await db.get_user_by_stripe_customer(stripe_customer_id)
            if user and new_plan:
                await db.update_subscription_plan(user["user_id"], new_plan)
                logger.info(f"Subscription updated for user {user['user_id']}: {new_plan}")
        
        elif event_type == "charge.failed":
            # Direct charge failure (one-time payment)
            charge = event_data
            payment_intent_id = charge.get("payment_intent")
            
            await db.mark_payment_failed(payment_intent_id)
            logger.warning(f"Charge failed: {payment_intent_id}")
        
        elif event_type == "invoice.payment_succeeded":
            # Subscription renewal successful
            invoice = event_data
            subscription_id = invoice.get("subscription")
            
            if subscription_id:
                await db.extend_subscription(subscription_id, invoice.get("current_period_end"))
                logger.info(f"Subscription renewed: {subscription_id}")
        
        elif event_type == "customer.created":
            # New Stripe customer created — link to local user if not already
            customer = event_data
            email = customer.get("email")
            if email:
                user = await db.get_user_by_email(email)
                if user:
                    await db.link_stripe_customer(user["user_id"], customer["id"])
        
        else:
            # Unhandled event type — log but don't error
            logger.info(f"Unhandled Stripe webhook event: {event_type}")
            return {"status": "ignored", "event_type": event_type}
    
    except Exception as e:
        logger.error(f"Webhook processing failed for {event_type}: {e}", exc_info=True)
        # Return 500 to trigger retry
        return {"status": "error", "detail": "Processing failed"}, 500
    
    return {"status": "success", "event_type": event_type}


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
