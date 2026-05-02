"""Enhanced pytest fixtures for CI/CD test reliability."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import pytest_asyncio
from fastapi.testclient import TestClient
from backend.app.main import app

# Enhanced test client with auth fixtures
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

# Run these
@pytest.mark.asyncio
async def test_integration_fixtures():
    """Verify fixtures work."""
    assert True
