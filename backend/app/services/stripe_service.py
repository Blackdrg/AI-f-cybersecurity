"""Stripe SaaS Billing Service - Production Ready"""
import os
import stripe
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException
from ..db.db_client import get_db
from ..schemas import SubscriptionResponse, PaymentResponse

logger = logging.getLogger(__name__)

# Load Stripe keys from env/Vault
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
stripe.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_...")

class StripeBillingService:
    def __init__(self):
        self.db = get_db()
    
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
            
            await self.db.create_subscription(
                subscription_id, user_id, plan_id, "pending", expires_at
            )
            
            return SubscriptionResponse(
                subscription_id=subscription_id,
                user_id=user_id,
                plan_id=plan_id,
                status="pending",
                stripe_session=session.id,
                created_at=datetime.utcnow().isoformat()
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe create sub error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def handle_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process Stripe webhook events with idempotency."""
        event_id = event.get("id")
        if not event_id:
            raise HTTPException(status_code=400, detail="Missing event ID")

        # 1. Check if already processed
        if await self.db.is_webhook_event_processed(event_id):
            logger.info(f"Webhook event {event_id} already processed. Skipping.")
            return {"status": "already_processed"}

        # 2. Record event (pending)
        await self.db.record_webhook_event(event_id, event["type"], event)

        try:
            event_type = event["type"]
            
            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                user_id = session["metadata"].get("user_id")
                plan_id = session["metadata"].get("plan_id")
                subscription_id = str(session.get("subscription"))
                
                if not user_id or not plan_id:
                    logger.error(f"Missing metadata in session {session.get('id')}")
                    return {"status": "error", "message": "Missing metadata"}

                # Ensure user exists (create placeholder if missing)
                existing_user = await self.db.get_user_by_id(user_id)
                if existing_user is None:
                    await self.db.create_user(user_id, session.get("customer_email") or f"{user_id}@example.com", user_id, plan_id)
                
                # Ensure plan exists (minimal record)
                await self.db.execute("""
                    INSERT INTO plans (plan_id, name, price, currency, interval)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (plan_id) DO NOTHING
                """, plan_id, plan_id.title(), 29.99, 'USD', 'month')
                
                # Create or update subscription
                await self.db.update_subscription(subscription_id, user_id, plan_id, "active")
                logger.info(f"Subscription activated: {subscription_id}")
            
            elif event_type == "customer.subscription.deleted":
                sub = event["data"]["object"]
                subscription_id = str(sub["id"])
                await self.db.cancel_subscription(subscription_id)
                logger.info(f"Subscription cancelled: {subscription_id}")
            
            elif event_type == "invoice.payment_failed":
                invoice = event["data"]["object"]
                subscription_id = str(invoice.get("subscription"))
                await self.db.update_subscription(subscription_id, status="past_due")
                logger.warning(f"Payment failed for {subscription_id} - triggering background retry...")
                # Trigger Celery background task
                from ..tasks.payment_tasks import retry_failed_payment
                retry_failed_payment.delay(subscription_id)
            
            elif event_type == "invoice.payment_succeeded":
                invoice = event["data"]["object"]
                subscription_id = str(invoice.get("subscription"))
                await self.db.update_subscription(subscription_id, status="active")
                logger.info(f"Payment succeeded for {subscription_id}")

            # 3. Mark as processed
            await self.db.mark_webhook_processed(event_id)
            return {"status": "success"}
        
        except Exception as e:
            logger.error(f"Webhook handling error for {event_id}: {e}")
            # Keep as 'pending' for manual investigation or automatic retry
            raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
    
    async def get_customer_usage(self, customer_id: str) -> Dict[str, int]:
        """Metered billing usage for Stripe reports."""
        # Query DB usage logs
        usage = await self.db.get_monthly_usage(customer_id)
        return {
            "recognitions": usage.get("recognitions", 0),
            "enrollments": usage.get("enrollments", 0),
        }
    
    async def retry_failed_payment(self, subscription_id: str):
        """Async retry for failed payments (Celery)."""  
        sub = stripe.Subscription.retrieve(subscription_id)
        stripe.Subscription.modify(sub.subscription.id, payment_behavior='pending_if_incomplete')

# Global instance
billing_service = StripeBillingService()
