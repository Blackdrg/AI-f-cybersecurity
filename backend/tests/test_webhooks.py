"""Tests for webhook handling"""
import pytest
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def generate_signature(payload: bytes, secret: str = "whsec_change_me") -> str:
    """Generate HMAC signature for webhook."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.mark.webhooks
class TestStripeWebhooks:
    """Test Stripe webhook handling."""

    def test_webhook_requires_signature(self):
        """Test that webhooks require valid signature."""
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        
        response = client.post(
            "/api/webhooks/stripe",
            content=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 400 for missing signature
        assert response.status_code == 400
        assert "Missing signature" in response.json()["detail"]

    def test_valid_signature_accepted(self):
        """Test that valid signatures are accepted."""
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_123"}}
        }).encode()
        
        signature = generate_signature(payload)
        
        response = client.post(
            "/api/webhooks/stripe",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-stripe-signature": signature
            }
        )
        
        assert response.status_code == 200

    def test_checkout_completed_handling(self):
        """Test checkout.session.completed event."""
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "customer": "cus_123",
                    "subscription": "sub_premium"
                }
            }
        }).encode()
        
        signature = generate_signature(payload)
        
        response = client.post(
            "/api/webhooks/stripe",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-stripe-signature": signature
            }
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_subscription_deleted_handling(self):
        """Test customer.subscription.deleted event."""
        payload = json.dumps({
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "canceled"
                }
            }
        }).encode()
        
        signature = generate_signature(payload)
        
        response = client.post(
            "/api/webhooks/stripe",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-stripe-signature": signature
            }
        )
        
        assert response.status_code == 200


@pytest.mark.webhooks
class TestBiometricEventWebhook:
    """Test biometric event webhook."""

    def test_event_format_validation(self):
        """Test that events have correct format."""
        payload = json.dumps({
            "event_id": "evt_123",
            "type": "MATCH_FOUND",
            "person_id": "person_456",
            "confidence": 0.98,
            "timestamp": "2026-04-29T23:20:00Z"
        }).encode()
        
        signature = generate_signature(payload)
        
        response = client.post(
            "/api/webhooks/biometric-event",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-aif-signature": signature
            }
        )
        
        assert response.status_code == 200

    def test_missing_signature_rejected(self):
        """Test that missing signatures are rejected."""
        payload = json.dumps({"event_id": "evt_123"}).encode()
        
        response = client.post(
            "/api/webhooks/biometric-event",
            content=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401
