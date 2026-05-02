import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middleware.rate_limit import RedisRateLimiter

@pytest.mark.asyncio
async def test_sliding_window_rate_limit():
    """
    Test the Redis-backed sliding window logic.
    """
    redis_url = "redis://mock:6379"
    limiter = RedisRateLimiter(redis_url)
    await limiter.ensure_connected()
    
    key = "test_user_123"
    limit = 5
    window = 60
    
    # 1. First 5 requests should pass
    for i in range(limit):
        is_limited, remaining, reset, retry = await limiter.is_rate_limited(key, limit, window)
        assert is_limited is False, f"Request {i+1} should not be limited"
        assert remaining == (limit - (i + 1)), f"Remaining should be {limit - (i + 1)}, got {remaining}"
        
    # 2. 6th request should be limited
    is_limited, remaining, reset, retry = await limiter.is_rate_limited(key, limit, window)
    assert is_limited is True, "6th request should be rate limited"
    assert remaining == 0
    assert retry > 0, "retry_after should be positive"
    
    await limiter.client.flushdb()


@pytest.mark.asyncio
async def test_rate_limit_different_keys():
    """Test that different keys have independent limits."""
    redis_url = "redis://mock:6379"
    limiter = RedisRateLimiter(redis_url)
    await limiter.ensure_connected()
    
    key1 = "user_1"
    key2 = "user_2"
    limit = 3
    window = 60
    
    # Exhaust key1's limit
    for _ in range(3):
        await limiter.is_rate_limited(key1, limit, window)
    
    # key1 should be limited
    is_limited_1, _, _, _ = await limiter.is_rate_limited(key1, limit, window)
    assert is_limited_1 is True
    
    # key2 should still have full limit
    is_limited_2, remaining_2, _, _ = await limiter.is_rate_limited(key2, limit, window)
    assert is_limited_2 is False
    assert remaining_2 == limit - 1
    
    await limiter.client.flushdb()


@pytest.mark.asyncio
async def test_rate_limit_window_expiry():
    """Test that rate limits expire after the window."""
    redis_url = "redis://mock:6379"
    limiter = RedisRateLimiter(redis_url)
    await limiter.ensure_connected()
    
    key = "expiring_user"
    limit = 2
    window = 1  # 1 second window for testing
    
    # Exhaust the limit
    for _ in range(2):
        await limiter.is_rate_limited(key, limit, window)
    
    is_limited, _, _, _ = await limiter.is_rate_limited(key, limit, window)
    assert is_limited is True
    
    # Wait for window to expire
    await asyncio.sleep(1.5)
    
    # Should be allowed again after window expiry
    is_limited, remaining, _, _ = await limiter.is_rate_limited(key, limit, window)
    assert is_limited is False
    assert remaining == limit - 1
    
    await limiter.client.flushdb()


@pytest.mark.asyncio
async def test_rate_limit_headers():
    """Test that rate limit headers are correctly calculated."""
    redis_url = "redis://mock:6379"
    limiter = RedisRateLimiter(redis_url)
    await limiter.ensure_connected()
    
    key = "header_test_user"
    limit = 10
    window = 60
    
    # First request
    is_limited, remaining, reset, retry = await limiter.is_rate_limited(key, limit, window)
    assert is_limited is False
    assert remaining == 9
    assert reset > 0
    
    # After several requests
    for _ in range(5):
        await limiter.is_rate_limited(key, limit, window)
    
    # One more call to check headers (7th total)
    is_limited, remaining, reset, retry = await limiter.is_rate_limited(key, limit, window)
    assert is_limited is False
    assert remaining == 3  # 10 - 7 = 3 remaining
    
    await limiter.client.flushdb()


if __name__ == "__main__":
    pass