"""Tests for Stripe webhook handling in payments module"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPaymentsWebhook:
    """Test Stripe webhook handling in payments endpoint."""

    def test_webhook_requires_signature(self):
        """Test that webhooks require valid signature."""
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        
        response = client.post(
            "/api/payments/webhook",
            content=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400

    def test_valid_signature_accepted(self):
        """Test that valid signatures are accepted."""
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_123"}}
        }).encode()
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_123",
                        "metadata": {"user_id": "user_123", "plan_id": "plan_123"},
                        "amount_total": 2999,
                        "currency": "usd"
                    }
                }
            }
            
            with patch('app.api.payments.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_db.create_subscription = AsyncMock()
                mock_db.log_payment = AsyncMock()
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    "/api/payments/webhook",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "test_signature"
                    }
                )
                
                assert response.status_code == 200

    def test_invalid_payload(self):
        """Test that invalid payloads are rejected."""
        payload = b"invalid json"
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.side_effect = ValueError("Invalid payload")
            
            response = client.post(
                "/api/payments/webhook",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "test_signature"
                }
            )
            
            assert response.status_code == 400

    def test_checkout_completed_handling(self):
        """Test checkout.session.completed event handling."""
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "metadata": {"user_id": "user_123", "plan_id": "premium"},
                    "amount_total": 2999,
                    "currency": "usd",
                    "payment_intent": "pi_123",
                    "subscription": "sub_123"
                }
            }
        }).encode()
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = json.loads(payload.decode())
            
            with patch('app.api.payments.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_db.create_subscription = AsyncMock()
                mock_db.log_payment = AsyncMock()
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    "/api/payments/webhook",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "test_signature"
                    }
                )
                
                assert response.status_code == 200

    def test_unhandled_event_type(self):
        """Test that unhandled event types are logged but don't cause errors."""
        payload = json.dumps({
            "type": "some.random.event",
            "data": {"object": {"id": "evt_123"}}
        }).encode()
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = json.loads(payload.decode())
            
            response = client.post(
                "/api/payments/webhook",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "test_signature"
                }
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "ignored"