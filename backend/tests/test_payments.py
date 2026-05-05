"""Tests for payment processing"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token

client = TestClient(app)


class TestPayments:
    """Test payment processing endpoints."""

    @pytest.mark.asyncio
    async def test_create_payment_session(self):
        """Test creating a payment session."""
        from app.schemas import PaymentCreate
        
        payment_data = PaymentCreate(plan_id="premium", amount=29.99)
        
        # Create a valid JWT token for authentication
        token = create_token("user-123", "viewer")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock the payment provider's create_checkout_session method
        with patch('app.providers.MockPaymentProvider.create_checkout_session', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "session_id": "cs_123",
                "url": "https://checkout.stripe.com/test",
                "is_mock": True,
                "user_id": "user-123",
                "plan_id": "premium",
                "amount": 29.99
            }
            
            response = client.post(
                "/api/payments/create-session",
                json=payment_data.model_dump(),
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "url" in data
            mock_create.assert_called_once_with(
                user_id="user-123",
                plan_id="premium",
                amount=29.99
            )

    @pytest.mark.asyncio
    async def test_create_payment_session_invalid_data(self):
        """Test creating a payment session with invalid data."""
        # Missing plan_id
        payment_data = {"amount": 29.99}
        
        token = create_token("user-123", "viewer")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/api/payments/create-session",
            json=payment_data,
            headers=headers
        )
        
        # Should validate and return 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_payment_history(self):
        """Test getting payment history."""
        token = create_token("user-123", "viewer")
        headers = {"Authorization": f"Bearer {token}"}
        
        with patch('app.api.payments.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.get_payment_history = AsyncMock(return_value=[
                {
                    "payment_id": "pay_123",
                    "user_id": "user-123",
                    "amount": 29.99,
                    "currency": "USD",
                    "status": "succeeded",
                    "stripe_payment_id": "pi_123",
                    "created_at": "2026-01-01T00:00:00"
                }
            ])
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/payments/history", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["payment_id"] == "pay_123"
            assert data[0]["amount"] == 29.99

    @pytest.mark.asyncio
    async def test_generate_invoice(self):
        """Test generating a PDF invoice."""
        token = create_token("user-123", "viewer")
        headers = {"Authorization": f"Bearer {token}"}
        
        with patch('app.api.payments.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.pool = MagicMock()
            mock_db.pool.fetchrow = AsyncMock(return_value={
                "payment_id": "pay_123",
                "user_id": "user-123",
                "amount": 29.99,
                "currency": "USD",
                "status": "succeeded",
                "created_at": "2026-01-01T00:00:00"
            })
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/payments/invoice/pay_123", headers=headers)
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            # Note: We're not checking the PDF content in this test

    @pytest.mark.asyncio
    async def test_generate_invoice_not_found(self):
        """Test generating an invoice for a non-existent payment."""
        token = create_token("user-123", "viewer")
        headers = {"Authorization": f"Bearer {token}"}
        
        with patch('app.api.payments.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.pool = MagicMock()
            mock_db.pool.fetchrow = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/payments/invoice/pay_nonexistent", headers=headers)
            
            assert response.status_code == 404
            assert "Payment not found" in response.json()["detail"]
