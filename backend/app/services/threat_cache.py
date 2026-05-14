"""
Redis-backed Caching Layer for Threat Intelligence
Provides fast, persistent caching with TTL and invalidation.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class ThreatIntelCache:
    """Redis-backed cache for threat intelligence data."""

    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        """
        Initialize the cache layer.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds for cached entries
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None
        self._available = False

    async def connect(self):
        """Establish connection to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("redis-py not available, cache disabled")
            self._available = False
            return

        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self._client.ping()
            self._available = True
            logger.info("Threat Intel Cache connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, cache running in-memory mode")
            self._available = False
            self._memory_cache: Dict[str, Any] = {}
            self._memory_timestamps: Dict[str, datetime] = {}

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
        self._available = False

    @property
    def available(self) -> bool:
        """Check if cache backend is available."""
        return self._available

    # ──────────────────────────────────────────
    # IOC Lookup Cache
    # ──────────────────────────────────────────

    async def get_ioc(self, indicator: str, ioc_type: str) -> Optional[Dict[str, Any]]:
        """Get cached IOC result."""
        key = f"ioc:{ioc_type}:{indicator.lower()}"
        return await self._get(key)

    async def set_ioc(self, indicator: str, ioc_type: str, result: Dict[str, Any],
                      ttl: int = None):
        """Cache an IOC lookup result."""
        key = f"ioc:{ioc_type}:{indicator.lower()}"
        await self._set(key, result, ttl or self.default_ttl)

    async def invalidate_ioc(self, indicator: str, ioc_type: str):
        """Invalidate a specific IOC cache entry."""
        key = f"ioc:{ioc_type}:{indicator.lower()}"
        await self._delete(key)

    # ──────────────────────────────────────────
    # Feed Cache
    # ──────────────────────────────────────────

    async def get_feed(self, feed_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached threat feed data."""
        key = f"feed:{feed_name}"
        return await self._get(key)

    async def set_feed(self, feed_name: str, data: List[Dict[str, Any]],
                       ttl: int = None):
        """Cache threat feed data."""
        key = f"feed:{feed_name}"
        await self._set(key, data, ttl or self.default_ttl * 2)

    async def invalidate_feed(self, feed_name: str):
        """Invalidate feed cache."""
        key = f"feed:{feed_name}"
        await self._delete(key)

    # ──────────────────────────────────────────
    # Search Results Cache
    # ──────────────────────────────────────────

    async def get_search(self, query: str, provider: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        key = f"search:{provider}:{query.lower()}"
        return await self._get(key)

    async def set_search(self, query: str, provider: str, results: List[Dict[str, Any]],
                         ttl: int = None):
        """Cache search results."""
        key = f"search:{provider}:{query.lower()}"
        await self._set(key, results, ttl or self.default_ttl)

    # ──────────────────────────────────────────
    # Threat Score Cache
    # ──────────────────────────────────────────

    async def get_threat_score(self, indicator: str) -> Optional[int]:
        """Get cached threat score."""
        key = f"score:{indicator.lower()}"
        result = await self._get(key)
        if result is not None and isinstance(result, dict):
            return result.get("score")
        return None

    async def set_threat_score(self, indicator: str, score: int,
                               details: Dict[str, Any] = None, ttl: int = None):
        """Cache threat score with details."""
        key = f"score:{indicator.lower()}"
        value = {"score": score, "details": details or {}, "updated_at": datetime.utcnow().isoformat()}
        await self._set(key, value, ttl or self.default_ttl)

    # ──────────────────────────────────────────
    # Reputational Data Cache
    # ──────────────────────────────────────────

    async def get_reputation(self, entity_type: str, entity_value: str) -> Optional[Dict]:
        """Get cached reputation data."""
        key = f"reputation:{entity_type}:{entity_value.lower()}"
        return await self._get(key)

    async def set_reputation(self, entity_type: str, entity_value: str,
                             data: Dict[str, Any], ttl: int = None):
        """Cache reputation data."""
        key = f"reputation:{entity_type}:{entity_value.lower()}"
        await self._set(key, data, ttl or self.default_ttl * 2)

    # ──────────────────────────────────────────
    # Cache Analytics
    # ──────────────────────────────────────────

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._available and self._client:
            try:
                info = await self._client.info()
                return {
                    "available": True,
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0"),
                    "used_memory_peak_human": info.get("used_memory_peak_human", "0"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                    "hit_rate": await self._calculate_hit_rate(),
                    "keys_count": await self._client.dbsize()
                }
            except Exception as e:
                logger.error(f"Cache stats retrieval failed: {e}")
                return {"available": False, "error": str(e)}
        return {"available": self._available, "mode": "in-memory" if not self._available else "unknown"}

    async def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self._available and self._client:
            try:
                info = await self._client.info("stats")
                hits = info.get("keyspace_hits", 0)
                misses = info.get("keyspace_misses", 0)
                total = hits + misses
                return (hits / total) if total > 0 else 0.0
            except Exception:
                pass
        return 0.0

    async def flush_pattern(self, pattern: str):
        """Delete all cache entries matching a pattern."""
        if self._available and self._client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self._client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error(f"Cache flush pattern '{pattern}' failed: {e}")

    async def get_health_status(self) -> str:
        """Return cache health status."""
        if not self._available:
            return "in_memory_mode"
        try:
            await self._client.ping()
            return "healthy"
        except Exception:
            return "unhealthy"

    # ──────────────────────────────────────────
    # Internal Methods
    # ──────────────────────────────────────────

    async def _get(self, key: str) -> Optional[Any]:
        """Internal get with fallback to in-memory cache."""
        if self._available and self._client:
            try:
                value = await self._client.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis GET failed for key {key}: {e}")
        elif not self._available:
            # Fallback to in-memory cache
            if hasattr(self, '_memory_cache') and key in self._memory_cache:
                if key in self._memory_timestamps:
                    if datetime.utcnow() - self._memory_timestamps[key] < timedelta(seconds=self.default_ttl):
                        return self._memory_cache.get(key)
                    else:
                        del self._memory_cache[key]
                        del self._memory_timestamps[key]
        return None

    async def _set(self, key: str, value: Any, ttl: int):
        """Internal set with fallback to in-memory cache."""
        serialized = json.dumps(value, default=str)
        if self._available and self._client:
            try:
                await self._client.setex(key, ttl, serialized)
            except Exception as e:
                logger.error(f"Redis SET failed for key {key}: {e}")
        else:
            # Fallback to in-memory cache
            if not hasattr(self, '_memory_cache'):
                self._memory_cache = {}
                self._memory_timestamps = {}
            self._memory_cache[key] = value
            self._memory_timestamps[key] = datetime.utcnow()

    async def _delete(self, key: str):
        """Internal delete."""
        if self._available and self._client:
            try:
                await self._client.delete(key)
            except Exception as e:
                logger.error(f"Redis DELETE failed for key {key}: {e}")
        elif hasattr(self, '_memory_cache') and key in self._memory_cache:
            del self._memory_cache[key]
            if key in self._memory_timestamps:
                del self._memory_timestamps[key]