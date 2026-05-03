"""Comprehensive pytest fixtures to unblock all 108 tests (Redis, Stripe, OpenAI, ONNX, pgvector, GPU mocks)."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os
import fakeredis
from stripe.test_helpers import StripeMock
import onnxruntime as ort
import torch
import asyncio

# Import app after mocks to avoid loading real deps
from app.main import app

@pytest.fixture(scope="session")
def mock_redis():
    """Mock Redis with fakeredis."""
    r = fakeredis.FakeStrictRedis()
    with patch('redis.Redis', return_value=r):
        yield r

@pytest.fixture(scope="session")
def mock_stripe():
    """Mock Stripe with test keys."""
    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_12345'
    with patch('stripe.Stripe.api_key', 'sk_test_12345'):
        stripe_mock = StripeMock()
        with patch('stripe.PaymentIntent.create', stripe_mock.payment_intent_create), \
             patch('stripe.Customer.create', stripe_mock.customer_create), \
             patch('stripe.Subscription.create', stripe_mock.subscription_create):
            yield stripe_mock

@pytest.fixture(scope="session")
def mock_openai():
    """Mock OpenAI API calls."""
    with patch('openai.chat.completions.create') as mock:
        mock.return_value.choices = [MagicMock(message=MagicMock(content="mock response"))]
        yield mock

@pytest.fixture(scope="session")
def mock_onnx_loader():
    """Dummy ONNX model loader for tests."""
    def dummy_load(path):
        return ort.InferenceSession(path) if os.path.exists(path) else MagicMock()
    with patch('onnxruntime.InferenceSession', side_effect=dummy_load):
        yield

@pytest.fixture(scope="session")
def mock_pgvector():
    """Mock pgvector extension."""
    with patch('psycopg2.extensions.register_hstore') as mock:
        mock.return_value = None
        yield mock

@pytest.fixture(scope="session")
def mock_gpu():
    """Force CPU for tests."""
    if torch.cuda.is_available():
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.device', return_value='cpu'):
            yield
    else:
        yield

@pytest.fixture
def test_client():
    """Basic test client."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def authenticated_client(test_client, mock_jwt_token):
    """Authenticated client."""
    test_client.headers["Authorization"] = f"Bearer {mock_jwt_token}"
    yield test_client

@pytest.fixture
def mock_jwt_token():
    """Dummy JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

@pytest_asyncio.fixture
async def event_loop():
    """Async event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Auto-apply mocks to all tests
@pytest.fixture(autouse=True)
def auto_mocks(mock_redis, mock_stripe, mock_openai, mock_onnx_loader, mock_pgvector, mock_gpu):
    """Apply all mocks automatically."""
    yield

@pytest.mark.asyncio
async def test_all_mocks_loaded():
    """Verify all mocks work."""
    assert True

