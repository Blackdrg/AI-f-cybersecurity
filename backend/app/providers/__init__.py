from .payment_provider import PaymentProvider, StripeProvider, MockPaymentProvider
from .llm_provider import LLMProvider, OpenAIProvider, LocalLLMProvider
import os

def get_payment_provider() -> PaymentProvider:
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if api_key and api_key != "sk_test_...":
        return StripeProvider(api_key)
    return MockPaymentProvider()

def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAIProvider(api_key)
    return LocalLLMProvider()
