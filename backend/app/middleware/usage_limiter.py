"""
Usage Limiter Middleware for Multi-tenant Rate Limiting.

Enforces per-tenant usage quotas based on subscription tier.
Integrates with Redis for distributed rate limiting.
"""

import time
import asyncio
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

# Tier-based limits (requests per day)
TIER_DAILY_LIMITS = {
    "free": 100,
    "basic": 1000,
    "premium": 10000,
    "enterprise": 1000000,  # effectively unlimited
}

# Recognition endpoint weight (some endpoints count more)
ENDPOINT_WEIGHTS = {
    "/api/recognize": 1,
    "/api/enroll": 5,  # enrollment costs more
    "/api/v1/recognize": 1,
    "/api/v1/enroll": 5,
    "/api/stream_recognize": 1,
    "/api/video_recognize": 2,
}


class UsageLimiter(BaseHTTPMiddleware):
    """
    Multi-tenant usage limiter based on subscription tier.
    Uses Redis for atomic increment operations across processes.
    """

    def __init__(self, app, redis_url: str = "redis://localhost:6379"):
        super().__init__(app)
        self.redis_url = redis_url
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.local_cache: Dict[str, Tuple[int, float]] = {}  # user_id -> (count, expiry)
        self.local_cache_ttl = 60  # seconds

    async def dispatch(self, request: Request, call_next):
        # Skip usage tracking for health checks and static routes
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Extract user from request (requires auth middleware)
        user = getattr(request.state, "user", None)
        if user is None:
            # No user context - allow but skip tracking (for health checks, public endpoints)
            return await call_next(request)

        user_id = user.get("user_id") or user.get("sub")
        if not user_id:
            return await call_next(request)

        tier = user.get("subscription_tier", "free")
        daily_limit = TIER_DAILY_LIMITS.get(tier, 100)

        # Determine endpoint weight
        path = request.url.path
        weight = ENDPOINT_WEIGHTS.get(path, 1)

        # Check quota
        allowed, current, limit = await self._check_quota(user_id, tier, weight)

        if not allowed:
            logger.warning(f"Usage limit exceeded for user {user_id} on {path}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Daily quota exceeded: {current}/{limit} requests used",
                    "retry_after": 86400  # 24 hours in seconds
                }
            )

        # Proceed with request
        response = await call_next(request)

        # Log usage on success (2xx)
        if 200 <= response.status_code < 300:
            await self._increment_usage(user_id, tier, weight)

        return response

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get or create Redis connection pool."""
        if self.redis_pool is None:
            try:
                self.redis_pool = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Redis unavailable for usage limiter: {e}")
                return None
        return redis.Redis(connection_pool=self.redis_pool)

    async def _check_quota(self, user_id: str, tier: str, weight: int) -> Tuple[bool, int, int]:
        """
        Check if user has remaining quota.
        Returns (allowed, current_count, daily_limit).
        """
        daily_limit = TIER_DAILY_LIMITS.get(tier, 100) * weight

        # Check local cache first
        cache_key = f"usage:{user_id}"
        now = time.time()
        if cache_key in self.local_cache:
            count, expires_at = self.local_cache[cache_key]
            if now < expires_at:
                if count + weight <= daily_limit:
                    return True, count + weight, daily_limit
                else:
                    return False, count, daily_limit
            # expired - ignore

        # Check Redis
        r = await self._get_redis()
        if r is not None:
            try:
                redis_key = f"usage:daily:{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
                current = await r.incr(redis_key, weight)
                if current == weight:  # newly created
                    await r.expire(redis_key, 86400 + 300)  # 24h + 5m buffer
                # Update local cache
                self.local_cache[cache_key] = (current, now + self.local_cache_ttl)
                if current <= daily_limit:
                    return True, current, daily_limit
                else:
                    # Over limit - maybe decrement back? Let it expire
                    return False, current, daily_limit
            except Exception as e:
                logger.error(f"Redis check failed: {e}")

        # Fallback: allow if Redis unavailable (fail open for now)
        # In production you might want to fail closed to enforce limits strictly
        return True, 0, daily_limit

    async def _increment_usage(self, user_id: str, tier: str, weight: int):
        """
        Record usage. Already incremented in check with INCR,
        so this is for additional tracking/metadata if needed.
        """
        # Could log to metrics here
        pass

    async def get_usage_stats(self, user_id: str) -> Dict:
        """Get current usage stats for a user (for dashboard)."""
        r = await self._get_redis()
        if r is None:
            return {"error": "unavailable"}

        redis_key = f"usage:daily:{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
        current = await r.get(redis_key)
        if current is None:
            current = 0
        else:
            current = int(current)

        # Get tier from user profile (would need DB access)
        # Hardcoding for now; in real system fetch from DB or cache
        tier = "free"  # placeholder
        limit = TIER_DAILY_LIMITS.get(tier, 100)

        return {
            "used": current,
            "limit": limit,
            "remaining": max(0, limit - current),
            "reset_in_seconds": 86400 - (time.time() % 86400)
        }


# Factory function for dependency injection
_usage_limiter: Optional[UsageLimiter] = None


def get_usage_limiter() -> UsageLimiter:
    """Get the global usage limiter instance."""
    global _usage_limiter
    if _usage_limiter is None:
        raise RuntimeError("UsageLimiter not initialized. Call init_usage_limiter first.")
    return _usage_limiter


async def init_usage_limiter(redis_url: str = None) -> UsageLimiter:
    """Initialize global usage limiter."""
    global _usage_limiter
    if _usage_limiter is None:
        url = redis_url or "redis://localhost:6379"
        _usage_limiter = UsageLimiter(app=None, redis_url=url)
    return _usage_limiter
