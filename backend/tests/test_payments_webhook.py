"""Tests for Stripe webhook handling in payments module"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPaymentsWebhook:
    """Test Stripe webhook handling in payments endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_requires_signature(self):
        """Test that webhooks require valid signature."""
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        
        response = client.post(
            "/api/payments/webhook",
            content=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 400 for missing signature (not 401 as in webhooks.py)
        assert response.status_code == 400
        assert "Missing signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self):
        """Test that valid signatures are accepted."""
        # Since we can't easily generate a real Stripe signature without the secret,
        # we'll mock the stripe.Webhook.construct_event call
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
            
            # Mock the database calls
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
                        "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                    }
                )
                
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert response.json()["event_type"] == "checkout.session.completed"

    @pytest.mark.asyncio
    async def test_invalid_payload(self):
        """Test that invalid payloads are rejected."""
        payload = b"invalid json"
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.side_effect = ValueError("Invalid payload")
            
            response = client.post(
                "/api/payments/webhook",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                }
            )
            
            assert response.status_code == 400
            assert "Invalid payload" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_signature(self):
        """Test that invalid signatures are rejected."""
        import stripe
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            # We mock the class itself to avoid the constructor issue in some environments
            with patch('stripe.error.SignatureVerificationError', Exception):
                mock_construct.side_effect = Exception("Invalid signature")
                
                response = client.post(
                    "/api/payments/webhook",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                    }
                )
                
                assert response.status_code == 400
                assert "Invalid signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_checkout_completed_handling(self):
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
            
            # Mock the database calls
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
                        "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                    }
                )
                
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert response.json()["event_type"] == "checkout.session.completed"
                
                # Verify database calls were made
                mock_db.create_subscription.assert_called_once()
                mock_db.log_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscription_deleted_handling(self):
        """Test customer.subscription.deleted event handling."""
        payload = json.dumps({
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123"
                }
            }
        }).encode()
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = json.loads(payload.decode())
            
            # Mock the database calls
            with patch('app.api.payments.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_db.deactivate_subscription = AsyncMock()
                mock_db.get_user_by_stripe_customer = AsyncMock(return_value={"user_id": "cus_123"})
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    "/api/payments/webhook",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                    }
                )
                
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert response.json()["event_type"] == "customer.subscription.deleted"

    @pytest.mark.asyncio
    async def test_charge_failed_handling(self):
        """Test charge.failed event handling."""
        payload = json.dumps({
            "type": "charge.failed",
            "data": {
                "object": {
                    "id": "ch_123",
                    "payment_intent": "pi_123"
                }
            }
        }).encode()
        
        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = json.loads(payload.decode())
            
            # Mock the database calls
            with patch('app.api.payments.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_db.mark_payment_failed = AsyncMock()
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    "/api/payments/webhook",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                    }
                )
                
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert response.json()["event_type"] == "charge.failed"
                
                # Verify database calls were made
                mock_db.mark_payment_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_unhandled_event_type(self):
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
                    "Stripe-Signature": "t=1234567890,v1=abc123,def456"
                }
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "ignored"
            assert response.json()["event_type"] == "some.random.event"
