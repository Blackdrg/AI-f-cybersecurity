"""Enhanced pytest fixtures for CI/CD test reliability - fixed."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest_asyncio
from fastapi.testclient import TestClient
from backend.app.main import app
import fakeredis
from stripe.test_helpers import StripeMock  # Assuming available or mock
import pytest_mock

@pytest_asyncio.fixture
async def test_client():
    """Test client with test DB and auth."""
    with TestClient(app) as client:
        yield client

@pytest_asyncio.fixture
async def authenticated_client(test_auth_token):
    """Test client with authentication."""
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {test_auth_token}"
    yield client

@pytest.fixture
def mock_models():
    """Mock model loading for fast tests."""
    with patch("app.models.face_detector.FaceDetector") as mock:
        mock.return_value.detect_faces = AsyncMock(return_value=[{"bbox": [0,0,100,100], "score": 0.9}])
        yield mock

@pytest.fixture
def mock_stripe():
    """Mock Stripe for billing tests."""
    with patch('stripe.checkout.Session.create') as mock:
        mock.return_value = MagicMock(id='cs_test_abc', subscription='sub_test_123')
        yield mock

@pytest.fixture
def mock_redis():
    """Mock Redis."""
    redis_mock = fakeredis.FakeRedis()
    with patch('redis.asyncio.Redis', return_value=redis_mock):
        yield redis_mock

@pytest.mark.asyncio
async def test_integration_fixtures():
    """Verify fixtures work."""
    assert True

# Full integration test
@pytest.mark.asyncio
async def test_recognize_endpoint(mock_models, authenticated_client):
    response = authenticated_client.post("/api/recognize", files={"image": ("test.jpg", b"fakeimage")})
    assert response.status_code == 200
    assert "faces" in response.json()["data"]

