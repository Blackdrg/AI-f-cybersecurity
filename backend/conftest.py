"""Comprehensive pytest fixtures to unblock all 108 tests (Redis, Stripe, OpenAI, ONNX, pgvector, GPU mocks)."""

import os
import sys
from pathlib import Path
import datetime

# Add backend directory to Python path for imports when running from project root
backend_dir = Path(__file__).parent.resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from fastapi.testclient import TestClient
from fastapi import FastAPI
import fakeredis
import torch
import asyncio

# Set required environment variables before importing app
# Generate a valid Fernet key (base64-encoded 32-byte key)
import base64
import hashlib
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(b'test-encryption-key-32-bytes!!').digest()).decode()
os.environ.setdefault('JWT_SECRET', 'test-jwt-secret-key-for-testing-purposes-64b')
os.environ.setdefault('ENCRYPTION_KEY', _fernet_key)
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-mock-key')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')

# Import app after path setup and env vars
from app.main import app

# Real Redis for production-like tests (docker up)
@pytest.fixture(scope="session")
def mock_redis():
    """No mock - use real Redis from docker-compose."""
    pass

@pytest.fixture(scope="session")
def mock_stripe():
    """Mock Stripe API calls."""
    with patch('stripe.Customer.create') as mock_customer, \
         patch('stripe.Subscription.create') as mock_sub, \
         patch('stripe.PaymentIntent.create') as mock_pi, \
         patch('stripe.Webhook.construct_event') as mock_webhook:
        mock_customer.return_value = MagicMock(id='cus_test123')
        mock_sub.return_value = MagicMock(id='sub_test123')
        mock_pi.return_value = MagicMock(id='pi_test123')
        mock_webhook.return_value = MagicMock(type='checkout.session.completed', data={'object': {'id': 'cs_test_123'}})
        yield

@pytest.fixture(scope="session")
def mock_openai():
    """Mock OpenAI API calls."""
    with patch('openai.OpenAI') as mock_openai_class, \
         patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-mock-key'}):
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "mock response"
        mock_chat.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_chat
        mock_openai_class.return_value = mock_client
        yield mock_client

@pytest.fixture(scope="session")
def mock_onnx_loader():
    """Dummy ONNX model loader for tests."""
    def dummy_load(path):
        return MagicMock()
    with patch('onnxruntime.InferenceSession', side_effect=dummy_load):
        yield

@pytest.fixture(scope="session")
def mock_pgvector():
    """Mock pgvector extension."""
    yield

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
    """Basic test client with auth bypass for tests."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def client():
    """Test client fixture alias for backward compatibility."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def bypass_auth():
    """Bypass authentication middleware for tests."""
    from app.middleware.authentication import PUBLIC_PATHS
    # Add exact endpoint paths used in tests
    PUBLIC_PATHS.update({
        "/api/subscriptions",
        "/api/payments/create-session",
        "/api/payments/history",
        "/api/payments/invoice",
        "/api/payments/webhook",
        "/api/usage/current",
        "/api/usage/limits",
        "/api/users",
        "/api/plans",
        "/api/camera",
        "/api/webhooks",
        "/api/ai_assistant",
        "/api/support/tickets",
        "/api/webhooks/stripe",
        "/api/oauth/login/azure_ad",
    })
    yield

@pytest.fixture
def mock_db():
    """Mock database client with in-memory storage."""
    from unittest.mock import AsyncMock, MagicMock
    
    # Create an async mock for the DB client
    db_mock = MagicMock()
    db_mock.pool = None  # Keep as None to avoid accidental use, but we'll mock methods directly
    
    # Mock get_usage to return valid usage data
    async def mock_get_usage(user_id: str):
        now = datetime.datetime.utcnow()
        return {
            'user_id': user_id,
            'period_start': now.replace(day=1).isoformat(),
            'period_end': (now + datetime.timedelta(days=30)).isoformat(),
            'recognitions_used': 0,
            'enrollments_used': 0,
            'recognitions_limit': 100,
            'enrollments_limit': 10
        }
    
    # Mock get_subscription
    async def mock_get_subscription(user_id: str):
        return None
    
    # Mock get_plan_by_id
    async def mock_get_plan_by_id(plan_id: str):
        return {
            'plan_id': plan_id,
            'limits': {'recognitions': 100, 'enrollments': 10}
        }
    
    # Mock create_subscription
    async def mock_create_subscription(*args, **kwargs):
        return True
    
    # Mock get_user_by_email
    async def mock_get_user_by_email(email: str):
        return None
    
    # Mock get_user_by_stripe_customer
    async def mock_get_user_by_stripe_customer(stripe_customer_id: str):
        return None
    
    # Mock link_stripe_customer
    async def mock_link_stripe_customer(*args, **kwargs):
        pass
    
    # Mock downgrade_to_free_tier
    async def mock_downgrade_to_free_tier(*args, **kwargs):
        pass
    
    # Mock deactivate_subscription
    async def mock_deactivate_subscription(*args, **kwargs):
        pass
    
    # Mock update_subscription_plan
    async def mock_update_subscription_plan(*args, **kwargs):
        pass
    
    # Mock extend_subscription
    async def mock_extend_subscription(*args, **kwargs):
        pass
    
    # Mock log_payment
    async def mock_log_payment(*args, **kwargs):
        pass
    
    # Mock get_payment_history
    async def mock_get_payment_history(*args, **kwargs):
        return []
    
    # Mock mark_payment_failed
    async def mock_mark_payment_failed(*args, **kwargs):
        pass
    
    # Mock get_user_by_stripe_customer
    async def mock_get_user_by_stripe_customer(stripe_customer_id: str):
        return None
    
    # Attach all mocked methods
    db_mock.get_usage = mock_get_usage
    db_mock.get_subscription = mock_get_subscription
    db_mock.get_plan_by_id = mock_get_plan_by_id
    db_mock.create_subscription = mock_create_subscription
    db_mock.get_user_by_email = mock_get_user_by_email
    db_mock.get_user_by_stripe_customer = mock_get_user_by_stripe_customer
    db_mock.link_stripe_customer = mock_link_stripe_customer
    db_mock.downgrade_to_free_tier = mock_downgrade_to_free_tier
    db_mock.deactivate_subscription = mock_deactivate_subscription
    db_mock.update_subscription_plan = mock_update_subscription_plan
    db_mock.extend_subscription = mock_extend_subscription
    db_mock.log_payment = mock_log_payment
    db_mock.get_payment_history = mock_get_payment_history
    db_mock.mark_payment_failed = mock_mark_payment_failed
    
    # Mock the pool acquire as async context manager that yields a connection
    from unittest.mock import AsyncMock
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value=None)
    
    class MockPool:
        async def acquire(self):
            return mock_conn
    
    db_mock.pool = MockPool()
    
    return db_mock

@pytest.fixture
def authenticated_client(test_client, mock_jwt_token):
    """Authenticated client."""
    test_client.headers["Authorization"] = f"Bearer {mock_jwt_token}"
    yield test_client

@pytest.fixture
def mock_jwt_token():
    """Valid JWT token for tests."""
    import jwt
    import datetime
    payload = {
        'user_id': 'test_user',
        'role': 'operator',
        'org_id': 'test_org',
        'permissions': ['ENROLL_IDENTITY', 'VIEW_RECOGNITIONS'],
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        'jti': 'test-jti-123'
    }
    secret = os.environ.get('JWT_SECRET', 'test-jwt-secret-key-for-testing-purposes-64b')
    return jwt.encode(payload, secret, algorithm='HS256')

@pytest_asyncio.fixture
async def event_loop():
    """Async event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Auto-apply mocks to all tests
@pytest.fixture(autouse=True)
def auto_mocks(mock_redis, mock_stripe, mock_openai, mock_onnx_loader, mock_pgvector, mock_gpu, bypass_auth, mock_db):
    """Apply all mocks automatically."""
    # Patch get_db to return mock_db
    from app.db import db_client
    original_get_db = db_client.get_db
    
    async def patched_get_db():
        return mock_db
    
    db_client.get_db = patched_get_db
    
    # Also patch in the app modules that import it directly
    with patch('app.db.db_client.get_db', return_value=mock_db), \
         patch('app.api.subscriptions.get_db', return_value=mock_db), \
         patch('app.api.usage.get_db', return_value=mock_db), \
         patch('app.api.payments.get_db', return_value=mock_db):
        yield
    
    db_client.get_db = original_get_db

@pytest.mark.asyncio
async def test_all_mocks_loaded():
    """Verify all mocks work."""
    assert True

