import pytest
import asyncio
from fastapi import Request
from app.middleware.rate_limit import RedisRateLimiter

@pytest.mark.asyncio
async def test_sliding_window_rate_limit():
    """
    Test the Redis-backed sliding window logic.
    """
    # Use local redis for testing
    redis_url = "redis://localhost:6379/1"
    limiter = RedisRateLimiter(redis_url)
    
    key = "test_user_123"
    limit = 5
    window = 60
    
    # 1. First 5 requests should pass
    for i in range(limit):
        is_limited, remaining, reset, retry = await limiter.is_rate_limited(key, limit, window)
        assert is_limited is False
        assert remaining == (limit - (i + 1))
        
    # 2. 6th request should be limited
    is_limited, remaining, reset, retry = await limiter.is_rate_limited(key, limit, window)
    assert is_limited is True
    assert remaining == 0
    assert retry > 0
    
    # Clean up
    await limiter.client.flushdb()

if __name__ == "__main__":
    # To run manually: pytest backend/tests/test_rate_limit.py
    pass
