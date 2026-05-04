import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_auth_token():
    return 'test.jwt.token.123'
