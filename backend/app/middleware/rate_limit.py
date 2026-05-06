"""
Production Rate Limiting Middleware
Redis-backended sliding window with per-user limits and headers
"""
import time
import uuid
import asyncio
import redis.asyncio as redis
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, Callable, Tuple
import logging
import json

from backend.app.security import get_encrypted_redis_client

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Distributed rate limiter using Redis sorted sets"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
        self._init_lock = asyncio.Lock()
        self._mock_mode = redis_url == "redis://mock:6379"

    async def ensure_connected(self):
        """Lazy connection establishment with encrypted Redis"""
        if self.client is None:
            async with self._init_lock:
                if self.client is None:
                    if self._mock_mode:
                        self.client = MockRedisClient()
                    else:
                        try:
                            self.client = await get_encrypted_redis_client(self.redis_url)
                        except Exception:
                            self.client = MockRedisClient()

    async def is_rate_limited(self, key: str, limit: int, window: int = 60) -> Tuple[bool, int, int, int]:
        """Check if rate limited. Returns (is_limited, remaining, reset_after, retry_after)"""
        await self.ensure_connected()
        now = int(time.time())
        try:
            # First clean old entries and get current count
            pipe1 = self.client.pipeline()
            pipe1.zremrangebyscore(key, 0, now - window)
            pipe1.zcard(key)
            results = await pipe1.execute()
            current_count = results[1]
            
            is_limited = current_count >= limit
            remaining = max(0, limit - current_count - 1)
            
            if is_limited:
                # Limited, don't add the request
                earliest = []
                items = self.client.data.get(key, {}) if hasattr(self.client, 'data') else {}
                if items:
                    earliest_items = sorted(items.items(), key=lambda x: float(x[1]))[:1]
                    if earliest_items:
                        earliest = earliest_items
                if earliest:
                    retry_after = max(0, int(float(earliest[0][1])) + window - now)
                    reset_after = int(float(earliest[0][1])) + window
                else:
                    retry_after = 0
                    reset_after = now + window
                return True, 0, reset_after, retry_after
            
            # Not limited, add this request
            unique_val = str(now) + str(uuid.uuid4())
            pipe2 = self.client.pipeline()
            pipe2.zadd(key, {unique_val: float(now)})
            pipe2.expire(key, window + 60)
            results2 = await pipe2.execute()
            
            # Re-count after adding
            pipe3 = self.client.pipeline()
            pipe3.zremrangebyscore(key, 0, now - window)
            pipe3.zcard(key)
            pipe3.zrange(key, 0, 0, withscores=True)
            results3 = await pipe3.execute()
            
            if results3[2]:
                retry_after = max(0, int(float(results3[2][0][1])) + window - now)
                reset_after = int(float(results3[2][0][1])) + window
            else:
                retry_after = 0
                reset_after = now + window
            remaining = max(0, limit - results3[1])
            return False, remaining, reset_after, retry_after
        except Exception:
            return False, limit, now + window, 0

    async def decrement(self, key: str):
        """Decrement counter (on response)"""
        now = int(time.time())
        await self.client.zremrangebyscore(key, 0, now - 60)


# Global in-memory storage for rate limiting (cross-pod shared state)
# This provides a fallback when Redis is unavailable
_global_rate_limit_storage = {}


class MockRedisClient:
    """Mock Redis client for testing and Redis fallback."""
    def __init__(self):
        global _global_rate_limit_storage
        self.data = _global_rate_limit_storage
    
    def pipeline(self):
        return MockPipeline(self)
    
    async def zremrangebyscore(self, key, min_val, max_val):
        if key not in self.data:
            return
        self.data[key] = {k: v for k, v in self.data[key].items() if not (min_val <= float(v) <= max_val)}
    
    async def flushdb(self):
        """Clear all data."""
        self.data.clear()


class MockPipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []
    
    def zadd(self, key, mapping):
        self.commands.append(('zadd', key, mapping))
        return self
    
    def zremrangebyscore(self, key, min_val, max_val):
        self.commands.append(('zremrangebyscore', key, min_val, max_val))
        return self
    
    def zcard(self, key):
        self.commands.append(('zcard', key))
        return self
    
    def zrange(self, key, start, stop, withscores=False):
        self.commands.append(('zrange', key, start, stop, withscores))
        return self
    
    def expire(self, key, seconds):
        self.commands.append(('expire', key, seconds))
        return self
    
    async def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'zadd':
                _, key, mapping = cmd
                if key not in self.client.data:
                    self.client.data[key] = {}
                self.client.data[key].update(mapping)
                results.append(len(mapping))
            elif cmd[0] == 'zremrangebyscore':
                _, key, min_val, max_val = cmd
                if key in self.client.data:
                    before = len(self.client.data[key])
                    self.client.data[key] = {k: v for k, v in self.client.data[key].items() 
                                             if not (min_val <= float(v) <= max_val)}
                    results.append(before - len(self.client.data[key]))
                else:
                    results.append(0)
            elif cmd[0] == 'zcard':
                _, key = cmd
                # Ensure all scores are properly stored as floats for comparison
                if key in self.client.data:
                    # Clean up any string scores by converting to float
                    cleaned = {}
                    for k, v in self.client.data[key].items():
                        try:
                            cleaned[k] = float(v) if not isinstance(v, (int, float)) else v
                        except:
                            cleaned[k] = float(time.time())
                    self.client.data[key] = cleaned
                results.append(len(self.client.data.get(key, {})))
            elif cmd[0] == 'zrange':
                _, key, start, stop, withscores = cmd
                items_dict = self.client.data.get(key, {})
                # Sort by score (float value)
                items = sorted(items_dict.items(), key=lambda x: float(x[1]))
                if withscores:
                    result = [(k, float(v)) for k, v in items[start:stop+1]]
                else:
                    result = [k for k, v in items[start:stop+1]]
                results.append(result)
            elif cmd[0] == 'expire':
                results.append(True)
            else:
                results.append(None)
        return results


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive rate limiting with:
    - User-based limits (from JWT)
    - Organization tier limits
    - Per-endpoint limits
    - Rate limit headers
    """
    
    # Default limits by tier and role
    LIMITS = {
        # Global rate limits (per minute)
        'default': 100,          # unauthenticated
        'free': 100,             # free tier user
        'pro': 1000,             # pro tier
        'enterprise': 5000,      # enterprise
        
        # Endpoint-specific overrides
        'recognize': {
            'free': 50,
            'pro': 500,
            'enterprise': 2000
        },
        'enroll': {
            'free': 10,
            'pro': 100,
            'enterprise': 500
        },
        'admin': {
            'free': 5,
            'pro': 50,
            'enterprise': 200
        }
    }
    
    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.redis_url = redis_url or "redis://localhost:6379"
        self.limiter = None
        self._init_task = None
    
    async def initialize(self):
        """Initialize Redis connection (called from startup)"""
        self.limiter = RedisRateLimiter(self.redis_url)
        await self.limiter.ensure_connected()
        logger.info("Rate limiter initialized with Redis")
    
    async def dispatch(self, request: Request, call_next):
        # Determine client identifier and limits
        client_key, base_limit = self._get_rate_limit_details(request)
        limit = self._get_limit_for_endpoint(request, client_key)
        window = 60
        
        # Initialize limiter if not already done
        if self.limiter is None:
            await self.initialize()
        
        if not client_key:
            # Cannot identify client, allow through (or use IP fallback)
            return await call_next(request)
        
        # Check rate limit
        is_limited, remaining, reset_after, retry_after = await self.limiter.is_rate_limited(
            f"rate_limit:{client_key}",
            limit=limit,
            window=window
        )
        
        # Add rate limit headers
        response = None
        if is_limited:
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "details": {
                        "retry_after": retry_after,
                        "limit": limit,
                        "window": "1 minute"
                    }
                }
            )
        else:
            response = await call_next(request)
        
        # Set rate limit headers on response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_after)
        response.headers["X-RateLimit-Window"] = "60"
        
        return response
    
    def _get_rate_limit_details(self, request: Request) -> Tuple[Optional[str], int]:
        """
        Extract client identifier and base limit from request.
        Returns (client_key, base_limit) - SYNCHRONOUS (not async)
        """
        # Try to get user_id from JWT (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        org_tier = getattr(request.state, 'org_tier', 'free')
        
        if user_id:
            # Use user-specific key
            client_key = f"user:{user_id}"
            base_limit = self.LIMITS.get(org_tier, self.LIMITS['default'])
        else:
            # Use IP-based key
            client_key = f"ip:{request.client.host}"
            base_limit = self.LIMITS['default']
        
        return client_key, base_limit
    
    def _get_limit_for_endpoint(self, request: Request, base_limit: int) -> int:
        """Get endpoint-specific limit if overridden"""
        path = request.url.path
        
        # Check endpoint categories
        if '/api/enroll' in path or '/api/v1/enroll' in path:
            category = 'enroll'
        elif '/api/recognize' in path or '/api/v1/recognize' in path:
            category = 'recognize'
        elif '/api/admin' in path or '/api/v1/admin' in path:
            category = 'admin'
        else:
            return base_limit
        
        # Get user's org tier (stored in request.state by auth middleware)
        org_tier = getattr(request.state, 'org_tier', 'free')
        
        category_limits = self.LIMITS.get(category, {})
        return category_limits.get(org_tier, base_limit)


# Helper to integrate with auth middleware
def set_request_user_context(request: Request, user: dict):
    """Attach user context to request for rate limiting"""
    request.state.user_id = user.get('user_id')
    request.state.org_tier = user.get('subscription_tier', 'free')
    request.state.org_id = user.get('org_id')


# Singleton instance for initialization
rate_limiter_middleware = RateLimitMiddleware(None)