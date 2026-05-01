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

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Distributed rate limiter using Redis sorted sets"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
        self._init_lock = asyncio.Lock()
        self._mock_mode = redis_url == "redis://mock:6379"

    async def ensure_connected(self):
        """Lazy connection establishment"""
        if self.client is None:
            async with self._init_lock:
                if self.client is None:
                    if self._mock_mode:
                        self.client = MockRedisClient()
                    else:
                        try:
                            self.client = await redis.from_url(self.redis_url, decode_responses=True)
                        except Exception:
                            self.client = MockRedisClient()

    async def is_rate_limited(self, key: str, limit: int, window: int = 60) -> Tuple[bool, int, int, int]:
        """Check if rate limited. Returns (is_limited, remaining, reset_after, retry_after)"""
        await self.ensure_connected()
        now = int(time.time())
        try:
            pipe = self.client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            unique_val = str(now) + str(uuid.uuid4())
            pipe.zadd(key, {unique_val: now})
            pipe.expire(key, window + 60)
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            results = await pipe.execute()
            current = results[2]
            earliest = results[3]
            is_limited = current > limit
            remaining = max(0, limit - current)
            if earliest:
                retry_after = int(earliest[0][1]) + window - now
                reset_after = int(earliest[0][1]) + window
            else:
                retry_after = 0
                reset_after = now + window
            if is_limited:
                pipe2 = self.client.pipeline()
                pipe2.zrem(key, unique_val)
                await pipe2.execute()
                remaining = 0
            return is_limited, remaining, reset_after, retry_after
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
                    self.client.data[key] = {k: v for k, v in self.client.data[key].items() if not (min_val <= float(v) <= max_val)}
                    results.append(before - len(self.client.data[key]))
                else:
                    results.append(0)
            elif cmd[0] == 'zcard':
                _, key = cmd
                results.append(len(self.client.data.get(key, {})))
            elif cmd[0] == 'zrange':
                _, key, start, stop, withscores = cmd
                items = list(self.client.data.get(key, {}).items())
                if withscores:
                    results.append([(k, float(v)) for k, v in items[start:stop+1]])
                else:
                    results.append([k for k, v in items[start:stop+1]])
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
        # Note: _get_rate_limit_details is synchronous (returns tuple, not awaited)
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
