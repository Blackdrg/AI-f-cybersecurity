"""Stripe SaaS Billing Service - Production Ready"""
import os
import logging
import stripe
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
from pydantic import BaseModel
from ..db.db_client import get_db

class SubscriptionResponse(BaseModel):
    subscription_id: str
    user_id: str
    plan_id: str
    status: str
    stripe_session: str
    created_at: str
    expires_at: Optional[str] = None

logger = logging.getLogger(__name__)

# Validate Stripe key at module load
_stripe_key = os.getenv("STRIPE_SECRET_KEY")
if not _stripe_key:
    logger.error("STRIPE_SECRET_KEY environment variable is not set. Billing will fail.")
    env = os.getenv("ENVIRONMENT", "development")
    if env in ["production", "prod"]:
        raise RuntimeError("Missing STRIPE_SECRET_KEY - required for billing/subscriptions in production")
    _stripe_key = "sk_test_placeholder"  # fallback for dev only

stripe.api_key = _stripe_key

_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
if not _webhook_secret:
    logger.warning("STRIPE_WEBHOOK_SECRET not set - webhook signature verification disabled")
stripe.webhook_secret = _webhook_secret or "whsec_test_placeholder"

class StripeBillingService:
    def __init__(self):
        self._db = None

    async def _db_client(self):
        if self._db is None:
            self._db = await get_db()
        return self._db

    async def create_subscription(self, user_id: str, plan_id: str, email: str) -> SubscriptionResponse:
        """Create Stripe checkout session + DB record."""
        try:
            # Price IDs from Stripe dashboard (pro/enterprise)
            price_map = {
                "pro": "price_monthly_5k_recogs",
                "enterprise": "price_monthly_unlimited",
            }
            price_id = price_map.get(plan_id, price_map["pro"])

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?success=true",
                cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?cancel=true",
                customer_email=email,
                metadata={
                    "user_id": user_id,
                    "plan_id": plan_id,
                },
                expand=["latest_invoice.payment_intent"]
            )

# Optimistic DB record (webhook confirms)
            subscription_id = str(session.subscription)
            expires_at = datetime.utcnow() + timedelta(days=30)

            db = await self._db_client()
            await db.create_subscription(
                subscription_id, user_id, plan_id, "pending", expires_at
            )

            return SubscriptionResponse(
                subscription_id=subscription_id,
                user_id=user_id,
                plan_id=plan_id,
                status="pending",
                stripe_session=session.id,
                created_at=datetime.utcnow().isoformat(),
                expires_at=expires_at.isoformat()
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe create sub error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def handle_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process Stripe webhook events with idempotency."""
        event_id = event.get("id")
        if not event_id:
            raise HTTPException(status_code=400, detail="Missing event ID")

        db = await self._db_client()

        # 1. Check if already processed
        if await db.is_webhook_event_processed(event_id):
            logger.info(f"Webhook event {event_id} already processed. Skipping.")
            return {"status": "already_processed"}

        # 2. Record event (pending)
        await db.record_webhook_event(event_id, event["type"], event)

        try:
            event_type = event["type"]
            
            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                metadata = session.get("metadata", {})
                user_id = metadata.get("user_id")
                plan_id = metadata.get("plan_id")
                subscription_id = str(session.get("subscription"))

                if not user_id or not plan_id:
                    logger.warning(f"Missing metadata in session {session.get('id')}; skipping activation")
                    return {"status": "success", "message": "no metadata; skipped"}

                # Ensure user exists (create placeholder if missing)
                existing_user = await db.get_user_by_id(user_id)
                if existing_user is None:
                    await self.db.create_user(user_id, session.get("customer_email") or f"{user_id}@example.com", user_id, plan_id)
                
                # Ensure plan exists (minimal record)
                await db.execute("""
                    INSERT INTO plans (plan_id, name, price, currency, interval)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (plan_id) DO NOTHING
                """, plan_id, plan_id.title(), 29.99, 'USD', 'month')
                
                # Create or update subscription
                await db.update_subscription(subscription_id, user_id, plan_id, "active")
                logger.info(f"Subscription activated: {subscription_id}")
            
            elif event_type == "customer.subscription.deleted":
                sub = event["data"]["object"]
                subscription_id = str(sub["id"])
                await db.cancel_subscription(subscription_id)
                logger.info(f"Subscription cancelled: {subscription_id}")
            
            elif event_type == "invoice.payment_failed":
                invoice = event["data"]["object"]
                subscription_id = str(invoice.get("subscription"))
                await db.update_subscription(subscription_id, status="past_due")
                logger.warning(f"Payment failed for {subscription_id} - triggering background retry...")
                # Trigger Celery background task
                from ..tasks.payment_tasks import retry_failed_payment
                retry_failed_payment.delay(subscription_id)
            
            elif event_type == "invoice.payment_succeeded":
                invoice = event["data"]["object"]
                subscription_id = str(invoice.get("subscription"))
                await db.update_subscription(subscription_id, status="active")
                logger.info(f"Payment succeeded for {subscription_id}")

            # 3. Mark as processed
            await db.mark_webhook_processed(event_id)
            return {"status": "success"}
        
        except Exception as e:
            logger.error(f"Webhook handling error for {event_id}: {e}")
            # Keep as 'pending' for manual investigation or automatic retry
            raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
    
    async def get_customer_usage(self, customer_id: str) -> Dict[str, int]:
        """Metered billing usage for Stripe reports."""
        # Query DB usage logs
        db = await self._db_client()
        usage = await db.get_monthly_usage(customer_id)
        return {
            "recognitions": usage.get("recognitions", 0),
            "enrollments": usage.get("enrollments", 0),
        }
    
    # Global instance
billing_service = StripeBillingService()
