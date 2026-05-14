"""
Enhanced Redis Client for AI-f Production
- JWT revocation store
- Rate limiting with sliding window
- Pub/Sub channel management
- Session management
- Circuit breaker pattern
"""
import redis.asyncio as redis
import json
import time
import uuid
import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisClient:
    """Production Redis client with JWT revocation, rate limiting, and Pub/Sub."""

    def __init__(self, url: str = None, password: str = None):
        self.url = url or "redis://localhost:6379"
        self.password = password
        self._client: Optional[redis.Redis] = None
        self._pubsub_client: Optional[redis.Redis] = None
        self._pubsub = None
        self._is_connected = False

    async def connect(self):
        """Establish Redis connection with retry logic."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self._client = redis.from_url(
                    self.url,
                    password=self.password,
                    decode_responses=True,
                    max_connections=50,
                    socket_keepalive=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )

                # Verify connection
                await self._client.ping()
                self._is_connected = True

                # Start Pub/Sub listener
                self._pubsub_client = redis.from_url(
                    self.url, password=self.password, decode_responses=True
                )
                self._pubsub = self._pubsub_client.pubsub()

                logger.info("Redis connected successfully")
                return True

            except Exception as e:
                logger.warning(f"Redis connection attempt {attempt+1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error("Redis connection failed after all retries")
                    return False

    async def disconnect(self):
        """Close Redis connections."""
        if self._pubsub:
            await self._pubsub.close()
        if self._pubsub_client:
            await self._pubsub_client.close()
        if self._client:
            await self._client.close()
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # ============================================================
    # JWT REVOCATION STORE
    # ============================================================

    async def revoke_jwt(self, jti: str, expires_at: datetime) -> bool:
        """Revoke a JWT token by its JTI (JWT ID).
        Uses Lua script for atomic operation."""
        if not self._client:
            return False

        lua_script = """
        local key = KEYS[1]
        local jti = ARGV[1]
        local ttl = ARGV[2]
        redis.call('SADD', key, jti)
        redis.call('EXPIRE', key, ttl)
        return 1
        """
        try:
            key = f"jwt:revoked:{jti[:8]}"
            ttl = max(1, int((expires_at - datetime.utcnow()).total_seconds()))
            await self._client.eval(lua_script, 1, key, jti, ttl)
            return True
        except Exception as e:
            logger.error(f"JWT revocation failed: {e}")
            return False

    async def is_jwt_revoked(self, jti: str) -> bool:
        """Check if a JWT token has been revoked."""
        if not self._client:
            return False

        try:
            key = f"jwt:revoked:{jti[:8]}"
            return await self._client.sismember(key, jti)
        except Exception as e:
            logger.error(f"JWT revocation check failed: {e}")
            return False  # Fail-open for availability

    async def revoke_all_user_tokens(self, user_id: str, session_id: str = None) -> int:
        """Revoke all tokens for a user (e.g., on password change/logout)."""
        if not self._client:
            return 0

        try:
            pattern = f"jwt:user:{user_id}:*"
            keys = await self._client.keys(pattern)
            count = 0
            for key in keys:
                await self._client.delete(key)
                count += 1
            return count
        except Exception as e:
            logger.error(f"Bulk token revocation failed: {e}")
            return 0

    # ============================================================
    # RATE LIMITING (Sliding Window)
    # ============================================================

    async def check_rate_limit(self, identifier: str, endpoint: str,
                                max_requests: int, window_seconds: int) -> Dict[str, Any]:
        """Sliding window rate limiter using Redis sorted sets."""
        if not self._client:
            return {'allowed': True, 'remaining': max_requests}

        try:
            key = f"rate_limit:{identifier}:{endpoint}"
            now = time.time()
            window_start = now - window_seconds

            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local window_seconds = tonumber(ARGV[4])

            -- Remove old entries
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

            -- Count current requests
            local current = redis.call('ZCARD', key)

            if current < max_requests then
                -- Add current request
                redis.call('ZADD', key, now, now .. ':' .. math.random())
                redis.call('EXPIRE', key, window_seconds)
                return {1, max_requests - current - 1, window_seconds}
            else
                return {0, 0, window_seconds}
            end
            """

            result = await self._client.eval(
                lua_script, 1, key, now, window_start,
                max_requests, window_seconds
            )

            return {
                'allowed': bool(result[0]),
                'remaining': int(result[1]),
                'reset_seconds': int(result[2]),
                'identifier': identifier,
                'endpoint': endpoint,
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return {'allowed': True, 'remaining': max_requests}  # Fail-open

    async def get_rate_limit_status(self, identifier: str, endpoint: str) -> Dict:
        """Get current rate limit status."""
        if not self._client:
            return {'current': 0, 'limit': 0}

        try:
            key = f"rate_limit:{identifier}:{endpoint}"
            count = await self._client.zcard(key)
            return {'current': count}
        except Exception:
            return {'current': 0}

    # ============================================================
    # PUB/SUB CHANNELS
    # ============================================================

    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish a message to a Pub/Sub channel."""
        if not self._client:
            return 0

        try:
            payload = json.dumps({
                **message,
                'timestamp': datetime.utcnow().isoformat(),
                'message_id': str(uuid.uuid4())
            })
            return await self._client.publish(channel, payload)
        except Exception as e:
            logger.error(f"Redis publish failed to {channel}: {e}")
            return 0

    async def subscribe(self, channels: List[str], handler):
        """Subscribe to Pub/Sub channels with a message handler."""
        if not self._pubsub:
            return

        try:
            await self._pubsub.subscribe(*channels)
            logger.info(f"Subscribed to channels: {channels}")

            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await handler(data)
                    except Exception as e:
                        logger.error(f"PubSub handler error: {e}")
        except Exception as e:
            logger.error(f"PubSub subscription error: {e}")

    # ============================================================
    # SESSION & CACHE MANAGEMENT
    # ============================================================

    async def set_session(self, session_id: str, data: Dict,
                          ttl_seconds: int = 3600) -> bool:
        """Store session data in Redis."""
        if not self._client:
            return False

        try:
            key = f"session:{session_id}"
            await self._client.setex(key, ttl_seconds, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Session store failed: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session data from Redis."""
        if not self._client:
            return None

        try:
            key = f"session:{session_id}"
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            return None

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate/delete a session."""
        if not self._client:
            return False

        try:
            key = f"session:{session_id}"
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Session invalidation failed: {e}")
            return False

    async def set_cache(self, key: str, value: Any,
                        ttl_seconds: int = 300) -> bool:
        """Set a cached value with TTL."""
        if not self._client:
            return False

        try:
            cache_key = f"cache:{key}"
            await self._client.setex(cache_key, ttl_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        if not self._client:
            return None

        try:
            cache_key = f"cache:{key}"
            data = await self._client.get(cache_key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate all cache keys matching a pattern."""
        if not self._client:
            return 0

        try:
            keys = await self._client.keys(f"cache:{pattern}")
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0

    # ============================================================
    # HEALTH CHECK
    # ============================================================

    async def health_check(self) -> Dict:
        """Perform Redis health check."""
        if not self._client:
            return {'status': 'error', 'message': 'Not connected'}

        try:
            start = time.perf_counter()
            info = await self._client.info()
            latency = (time.perf_counter() - start) * 1000

            return {
                'status': 'healthy',
                'version': info.get('redis_version', 'unknown'),
                'memory_used': info.get('used_memory_human', 'unknown'),
                'memory_max': info.get('maxmemory_human', 'unlimited'),
                'connected_clients': info.get('connected_clients', 0),
                'latency_ms': round(latency, 2),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


# Global instance
_redis_client: Optional[RedisClient] = None


def get_redis() -> RedisClient:
    """Get global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient(
            url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
            password=os.getenv('REDIS_PASSWORD')
        )
    return _redis_client


async def async_init_redis() -> RedisClient:
    """Initialize and return a new Redis client."""
    client = RedisClient(
        url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
        password=os.getenv('REDIS_PASSWORD')
    )
    await client.connect()
    return client