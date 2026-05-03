"""Enhanced pytest fixtures for CI/CD test reliability."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest_asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from fakeredis.aioredis import FakeRedis
import stripe
from openai import AsyncOpenAI
from backend.app.main import app
from app.services.stripe_service import stripe_service
from app.services.openai_service import openai_client

# Override global clients for testing
@pytest.fixture(autouse=True)
def mock_global_clients(monkeypatch):
    """Mock stripe and openai globally for all tests."""
    monkeypatch.setattr("stripe.Stripe", MagicMock())
    monkeypatch.setattr("stripe stripe.api_key", "test_key")
    stripe_service.stripe_key = "test_key"
    
    monkeypatch.setattr("openai.OpenAI", AsyncOpenAI)
    openai_client.api_key = "test_key"

@pytest_asyncio.fixture
async def test_client():
    """Test client with test DB and auth."""
    with TestClient(app) as client:
        yield client

@pytest_asyncio.fixture
async def async_client():
    """Async httpx client for async tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def authenticated_client(test_auth_token):
    """Test client with authentication."""
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {test_auth_token}"
    yield client

@pytest_asyncio.fixture
def mock_redis():
    """Mock Redis with fakeredis."""
    redis = FakeRedis()
    yield redis
    redis.close()

@pytest.fixture
def test_auth_token():
    """Test JWT token."""
    return "test.jwt.token.123"

@pytest.fixture
def mock_models():
    """Mock model loading for fast tests."""
    with patch("backend.app.models.face_detector.FaceDetector") as mock:
        mock.return_value.detect_faces = AsyncMock(return_value=[{"bbox": [0,0,100,100], "score": 0.9}])
        yield mock

@pytest.fixture
def mock_stripe():
    """Mock Stripe API."""
    with patch("backend.app.services.stripe_service.stripe") as mock_stripe:
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
        mock_stripe.Subscription.create.return_value = MagicMock(id="sub_test123")
        yield mock_stripe

@pytest_asyncio.fixture
async def mock_openai():
    """Mock OpenAI API."""
    with patch("backend.app.services.openai_service.openai_client.chat.completions.create") as mock_chat:
        mock_chat.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="test response"))]
        )
        yield mock_chat

@pytest.mark.asyncio
async def test_integration_fixtures():
    """Verify fixtures work."""
    assert True
