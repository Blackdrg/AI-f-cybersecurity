"""
Production Rate Limiting Middleware
Redis-backended sliding window with per-user limits and headers
"""
import time
import asyncio
import redis.asyncio as redis
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, Callable
import logging
import json

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Distributed rate limiter using Redis sorted sets"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
        self._init_lock = asyncio.Lock()
    
    async def ensure_connected(self):
        """Lazy connection establishment"""
        if self.client is None:
            async with self._init_lock:
                if self.client is None:
                    self.client = await redis.from_url(self.redis_url, decode_responses=True)
    
    async def is_rate_limited(self, key: str, limit: int, window: int = 60) -> tuple[bool, int, int, int]:
        await self.ensure_connected()
        now = int(time.time())
        pipe = self.client.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        results = await pipe.execute()
        current = results[2]
        earliest = results[3]
        remaining = max(0, limit - current)
        is_limited = current > limit
        if earliest:
            retry_after = int(earliest[0][1]) + window - now
            reset_after = int(earliest[0][1]) + window
        else:
            retry_after = 0
            reset_after = now + window
        return is_limited, remaining, reset_after, retry_after
    
    async def decrement(self, key: str):
        """Decrement counter (on response)"""
        now = int(time.time())
        await self.client.zremrangebyscore(key, 0, now - 60)


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
        await self.limiter.init()
        logger.info("Rate limiter initialized with Redis")
    
    async def dispatch(self, request: Request, call_next):
        # Determine client identifier and limits
        client_key, limit, window = await self._get_rate_limit_details(request)
        
        if not client_key:
            # Cannot identify client, allow through (or use IP fallback)
            return await call_next(request)
        
        # Check rate limit
        is_limited, remaining, reset_after, retry_after = await self.limiter.is_rate_limited(
            f"rate_limit:{client_key}",
            limit=self._get_limit_for_endpoint(request, client_key),
            window=60
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
    
    def _get_rate_limit_details(self, request: Request) -> tuple[Optional[str], int]:
        """
        Extract client identifier and base limit from request.
        Returns (client_key, base_limit)
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
