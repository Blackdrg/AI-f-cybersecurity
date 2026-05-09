from .payment_provider import PaymentProvider, StripeProvider, MockPaymentProvider
from .llm_provider import LLMProvider, OpenAIProvider, LocalLLMProvider
import os
import logging

logger = logging.getLogger(__name__)


def get_payment_provider() -> PaymentProvider:
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if api_key and not api_key.startswith("sk_test_"):
        return StripeProvider(api_key)
    # Using mock provider - warn in production
    env = os.getenv("ENVIRONMENT", "development")
    if env in ["production", "prod"]:
        logger.error("CRITICAL: Stripe API key missing/invalid in production - using mock payment provider! Billing will NOT work.")
    else:
        logger.warning("Stripe API key not set - using mock payment provider (dev mode)")
    return MockPaymentProvider()

def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAIProvider(api_key)
    return LocalLLMProvider()
