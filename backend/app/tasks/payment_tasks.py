"""
Payment & Billing Celery Tasks
"""
import logging
from app.celery import celery_app
from app.services.stripe_service import billing_service
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.payment_tasks.retry_failed_payment")
def retry_failed_payment(subscription_id: str):
    """
    Celery task to retry a failed payment by modifying the subscription.
    """
    logger.info(f"Retrying failed payment for subscription: {subscription_id}")
    # Since stripe_service methods are async, we run them in an event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(billing_service.retry_failed_payment(subscription_id))
        return {"status": "retry_triggered", "subscription_id": subscription_id}
    except Exception as e:
        logger.error(f"Failed to retry payment for {subscription_id}: {e}")
        raise

@celery_app.task(name="app.tasks.payment_tasks.audit_billing_usage")
def audit_billing_usage(customer_id: str):
    """
    Periodic task to reconcile usage data between DB and Stripe.
    """
    logger.info(f"Auditing billing usage for customer: {customer_id}")
    loop = asyncio.get_event_loop()
    try:
        usage = loop.run_until_complete(billing_service.get_customer_usage(customer_id))
        # Logic to report to Stripe metered billing could go here
        return {"status": "audit_complete", "customer_id": customer_id, "usage": usage}
    except Exception as e:
        logger.error(f"Billing audit failed for {customer_id}: {e}")
        raise
