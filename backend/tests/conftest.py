import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture(autouse=True)
def mock_redis_limiter(monkeypatch):
    mock_limiter = MagicMock()
    mock_limiter.is_rate_limited = AsyncMock(return_value=(False, 10, 0, 0))
    mock_limiter.ensure_connected = AsyncMock()
    monkeypatch.setattr('app.middleware.rate_limit.RedisRateLimiter', lambda _: mock_limiter)