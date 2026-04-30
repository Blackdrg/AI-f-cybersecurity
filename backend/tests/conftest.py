"""
Pytest configuration and fixtures for AI-F backend tests.
Provides shared fixtures for authentication, database mocking, and test data.

CI/CD Support:
    - Set CI=true environment variable for offline test runs
    - Uses mock fixtures when external dependencies unavailable
"""

import pytest
import os
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# CI mode flag - enables offline/mocked test runs
CI_MODE = os.getenv("CI", "false").lower() == "true"


# Mock database for tests
@pytest.fixture
def mock_db():
    """Provide a mock database connection."""
    if CI_MODE:
        # CI mode: Use fully mocked database
        db_mock = MagicMock()
        db_mock.execute = MagicMock(return_value=MagicMock())
        db_mock.fetch = MagicMock(return_value=[])
        db_mock.get_user_by_email = MagicMock(return_value=None)
        db_mock.get_user_by_id = MagicMock(return_value=None)
        db_mock.create_user = MagicMock(return_value=True)
        yield db_mock
    else:
        with patch('app.db.db_client.get_db') as mock:
            db_mock = MagicMock()
            db_mock.execute = MagicMock(return_value=MagicMock())
            db_mock.fetch = MagicMock(return_value=[])
            mock.return_value = db_mock
            yield db_mock


# Mock Redis for caching tests
@pytest.fixture
def mock_redis():
    """Provide a mock Redis client."""
    if CI_MODE:
        # CI mode: Use mock Redis without external connection
        redis_mock = MagicMock()
        redis_mock.get = MagicMock(return_value=None)
        redis_mock.set = MagicMock(return_value=True)
        redis_mock.delete = MagicMock(return_value=True)
        redis_mock.exists = MagicMock(return_value=False)
        redis_mock.expire = MagicMock(return_value=True)
        yield redis_mock
    else:
        with patch('app.services.cache_manager.get_redis') as mock:
            redis_mock = MagicMock()
            redis_mock.get = MagicMock(return_value=None)
            redis_mock.set = MagicMock(return_value=True)
            redis_mock.delete = MagicMock(return_value=True)
            mock.return_value = redis_mock
            yield redis_mock


# Test authentication token
@pytest.fixture
def test_auth_token():
    """Generate a valid test authentication token."""
    from app.security import create_token
    return create_token("test_user", "viewer")


# Test admin authentication token
@pytest.fixture
def test_admin_token():
    """Generate a valid admin authentication token."""
    from app.security import create_token
    return create_token("test_admin", "admin")


# Auth headers for test requests
@pytest.fixture
def auth_headers(test_auth_token):
    """Provide authorization headers for test requests."""
    return {"Authorization": f"Bearer {test_auth_token}"}


# Admin auth headers for test requests
@pytest.fixture
def admin_headers(test_admin_token):
    """Provide admin authorization headers for test requests."""
    return {"Authorization": f"Bearer {test_admin_token}"}


# Mock face image for testing
@pytest.fixture
def mock_face_image():
    """Create a realistic synthetic face image for testing."""
    img = np.random.randint(160, 220, (112, 112, 3), dtype=np.uint8)
    # Add face-like features
    img[30:50, 40:70] = [100, 80, 60]  # Left eye region
    img[30:50, 75:105] = [100, 80, 60]  # Right eye region
    img[65:85, 55:95] = [150, 120, 100]  # Nose region
    img[90:105, 45:105] = [120, 90, 70]  # Chin region
    return img.astype(np.float32)


# Mock face bbox for testing
@pytest.fixture
def mock_face_bbox():
    """Provide a standard face bounding box for testing."""
    return [20, 20, 90, 90]  # [x1, y1, x2, y2]


# Mock landmarks for testing
@pytest.fixture
def mock_landmarks():
    """Provide mock facial landmarks for testing."""
    # Generate 68 random points as landmarks
    return np.random.randn(68, 2).astype(np.float32)


# TestClient fixture with app
@pytest.fixture
def test_client():
    """Provide a FastAPI test client."""
    from app.main import app
    return TestClient(app)


# Mock GPU availability
@pytest.fixture
def mock_no_gpu():
    """Mock GPU as unavailable for CPU-only tests."""
    with patch('torch.cuda.is_available', return_value=False):
        yield


# Mock httpOnly cookie mode for tests
@pytest.fixture
def mock_http_only_cookie():
    """Mock httpOnly cookie mode for testing."""
    with patch.dict(os.environ, {"USE_HTTP_ONLY_COOKIE": "true"}):
        yield


# Sample enrollment data
@pytest.fixture
def sample_enrollment_data():
    """Provide sample enrollment request data."""
    return {
        "name": "Test User",
        "consent": "true",
        "check_spoof": "true"
    }


# Sample recognition data
@pytest.fixture
def sample_recognition_data():
    """Provide sample recognition request data."""
    return {
        "top_k": 3,
        "threshold": 0.6,
        "enable_spoof_check": True
    }
