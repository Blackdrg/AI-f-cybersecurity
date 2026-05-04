import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os
import sys
import fakeredis
import asgi_lifespan
from httpx import AsyncClient
import asyncio

# Add backend to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

os.environ['REDIS_URL'] = 'redis://localhost:6379'
os.environ['JWT_SECRET'] = 'test-secret-key-do-not-use-in-production'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_pass'
os.environ['STRIPE_SECRET_KEY'] = 'sk_test_mock'
os.environ['OPENAI_API_KEY'] = 'sk_test_mock'
os.environ['ONNX_BUNDLE_PATH'] = '/models/onnx_bundle'

import stripe
stripe.api_key = 'sk_test_mock'

import openai
openai.api_key = 'sk_test_mock'

from app.main import app

@pytest.fixture(scope='function')
async def test_client():
    async with asgi_lifespan.run(app):
        async with AsyncClient(app=app, base_url='http://test') as client:
            yield client

@pytest.fixture(scope='session')
def mock_redis():
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_instance.ping = AsyncMock(return_value=True)
        mock_instance.get = AsyncMock(return_value=None)
        mock_instance.set = AsyncMock(return_value=True)
        mock_instance.delete = AsyncMock(return_value=True)
        mock_instance.hgetall = AsyncMock(return_value={})
        mock_instance.hset = AsyncMock(return_value=True)
        mock_instance.expire = AsyncMock(return_value=True)
        mock_redis.from_url.return_value = mock_instance
        yield mock_instance

@pytest.fixture(scope='session')
def mock_stripe():
    with patch('stripe.Customer') as mock_customer, patch('stripe.Subscription') as mock_sub, patch('stripe.PaymentIntent') as mock_pi:
        mock_customer.create.return_value = MagicMock(id='cus_test123', name='Test User', email='test@example.com')
        mock_customer.retrieve.return_value = MagicMock(id='cus_test123', name='Test User', email='test@example.com')
        mock_sub.create.return_value = MagicMock(id='sub_test123', status='active')
        mock_sub.retrieve.return_value = MagicMock(id='sub_test123', status='active')
        mock_pi.create.return_value = MagicMock(id='pi_test123', status='succeeded')
        yield

@pytest.fixture(scope='function')
def mock_openai():
    with patch('openai.AsyncOpenAI') as mock_client:
        mock_async = AsyncMock()
        mock_async.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='mock response'))]))
        mock_client.return_value = mock_async
        yield mock_async

@pytest.fixture(scope='session')
def mock_onnx_loader():
    mock_session = MagicMock()
    mock_session.run = MagicMock(return_value=[MagicMock()])
    def dummy_load(path):
        if os.path.exists(path):
            return mock_session
        return mock_session
    with patch('onnxruntime.InferenceSession', side_effect=dummy_load):
        yield mock_session

@pytest.fixture(scope='session')
def mock_pgvector():
    with patch('psycopg2.extensions.register_hstore') as mock:
        mock.return_value = None
        yield mock

@pytest.fixture(scope='session')
def mock_gpu():
    with patch('torch.cuda.is_available', return_value=False), patch('torch.cuda.device_count', return_value=0), patch('torch.device', return_value=torch.device('cpu')):
        yield

@pytest.fixture
def test_auth_token():
    import jwt
    from datetime import datetime, timedelta
    payload = {'user_id': 'test_user', 'role': 'operator', 'org_id': 'test_org', 'permissions': ['ENROLL_IDENTITY', 'VIEW_RECOGNITIONS'], 'iat': datetime.utcnow(), 'exp': datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, 'test-secret-key-do-not-use-in-production', algorithm='HS256')

@pytest.fixture
def authenticated_client(test_client, test_auth_token):
    test_client.headers['Authorization'] = f'Bearer {test_auth_token}'
    yield test_client

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(app=app, base_url='http://test') as client:
        yield client

@pytest.fixture(autouse=True)
def auto_mocks(mock_redis, mock_stripe, mock_openai, mock_onnx_loader, mock_pgvector, mock_gpu):
    yield

@pytest.mark.asyncio
async def test_all_mocks_loaded():
    assert True
