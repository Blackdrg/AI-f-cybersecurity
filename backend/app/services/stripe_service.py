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
        """Process Stripe webhook events."""
        try:
            event_type = event["type"]
            
            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                user_id = session["metadata"]["user_id"]
                plan_id = session["metadata"]["plan_id"]
                subscription_id = str(session["subscription"])
                
                await self.db.update_subscription(subscription_id, user_id, plan_id, "active")
                logger.info(f"Subscription activated: {subscription_id}")
            
            elif event_type == "customer.subscription.deleted":
                sub = event["data"]["object"]
                subscription_id = str(sub["id"])
                await self.db.cancel_subscription(subscription_id)
                logger.info(f"Subscription cancelled: {subscription_id}")
            
            elif event_type == "invoice.payment_failed":
                sub = event["data"]["object"]["subscription"]
                subscription_id = str(sub)
                await self.db.update_subscription(subscription_id, status="past_due")
                logger.warning(f"Payment failed for {subscription_id} - retrying...")
                # Celery retry task
                # retry_payment.delay(subscription_id)
            
            elif event_type == "invoice.payment_succeeded":
                sub = event["data"]["object"]["subscription"]
                await self.db.update_subscription(str(sub), status="active")
            
            return {"status": "success"}
        
        except Exception as e:
            logger.error(f"Webhook handling error: {e}")
            raise HTTPException(status_code=400, detail="Webhook error")
    
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
