from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import uuid
import stripe

class PaymentProvider(ABC):
    @abstractmethod
    async def create_checkout_session(self, user_id: str, plan_id: str, amount: float, currency: str = "usd") -> Dict[str, Any]:
        """Create a checkout session for payment."""
        pass

    @abstractmethod
    async def get_health_status(self) -> str:
        """Return 'healthy', 'degraded', or 'unhealthy'."""
        pass

class StripeProvider(PaymentProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        if self.api_key:
            stripe.api_key = self.api_key

    async def create_checkout_session(self, user_id: str, plan_id: str, amount: float, currency: str = "usd") -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Stripe API key not configured")
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f'Subscription - {plan_id}',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/cancel",
                metadata={
                    'user_id': user_id,
                    'plan_id': plan_id
                }
            )
            return {"session_id": session.id, "url": session.url}
        except Exception as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def get_health_status(self) -> str:
        if not self.api_key or self.api_key == "sk_test_...":
            return "unconfigured"
        try:
            # Simple check by listing small number of sessions
            stripe.checkout.Session.list(limit=1)
            return "healthy"
        except Exception:
            return "degraded"

class MockPaymentProvider(PaymentProvider):
    async def create_checkout_session(self, user_id: str, plan_id: str, amount: float, currency: str = "usd") -> Dict[str, Any]:
        session_id = f"mock_session_{uuid.uuid4().hex[:24]}"
        return {
            "session_id": session_id,
            "url": f"/payment/success?session_id={session_id}",
            "is_mock": True
        }

    async def get_health_status(self) -> str:
        return "healthy"
