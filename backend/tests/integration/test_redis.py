"""Redis integration tests.

Tests real Redis operations including:
- Connection and cluster mode
- Rate limiting with sliding window
- JWT revocation store
- Pub/Sub messaging
- Lua script execution (if used)
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta


@pytest.mark.redis
@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis operations."""

    async def test_redis_connection(self, real_redis):
        """Test basic Redis connectivity."""
        assert real_redis is not None
        pong = await real_redis.ping()
        assert pong is True

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_rate_limiting_sliding_window(self, real_redis):
        """Test sliding window rate limiting implementation."""
        # Simulate rate limiter key pattern: "rate_limit:{user_id}:{route}"
        user_id = "test_user_123"
        route = "/api/recognize"
        limit = 10
        window = 60  # 60 seconds
        
        key = f"rate_limit:{user_id}:{route}"
        
        # Use sorted set for sliding window
        async with real_redis.pipeline(transaction=True) as pipe:
            now = time.time()
            await pipe.zadd(key, {str(now): now})
            await pipe.zremrangebyscore(key, 0, now - window)
            await pipe.zcard(key)
            await pipe.expire(key, window)
            results = await pipe.execute()
        
        current_count = results[2]  # zcard result
        assert current_count == 1
        
        # Check TTL was set
        ttl = await real_redis.ttl(key)
        assert ttl > 0 and ttl <= window

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_rate_limit_exceeded(self, real_redis):
        """Test that rate limit enforcement works."""
        user_id = "test_user_456"
        route = "/api/enroll"
        limit = 3
        
        key = f"rate_limit:{user_id}:{route}"
        
        # Simulate 4 requests
        now = time.time()
        for _ in range(4):
            await real_redis.zadd(key, {str(now): now})
            await real_redis.zremrangebyscore(key, 0, now - 60)
            count = await real_redis.zcard(key)
            if count >= limit:
                break
        
        assert count >= limit

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_jwt_revocation_store(self, real_redis):
        """Test JWT token revocation storage and lookup."""
        jti = "test_jwt_id_12345"
        expiry = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        
        key = f"jwt_revoked:{jti}"
        
        # Revoke token
        await real_redis.setex(key, 3600, str(expiry))
        
        # Check it exists
        stored_expiry = await real_redis.get(key)
        assert stored_expiry == str(expiry)
        
        # Verify is_revoked returns True
        is_revoked = await real_redis.exists(key)
        assert is_revoked == 1
        
        # Token should auto-expire after TTL
        await real_redis.expire(key, 1)  # Set short TTL for test
        await asyncio.sleep(1.5)
        exists = await real_redis.exists(key)
        assert exists == 0

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_redis_pubsub(self, real_redis):
        """Test Pub/Sub messaging for real-time notifications."""
        messages_received = []
        
        async def subscriber():
            pubsub = real_redis.pubsub()
            await pubsub.subscribe("test_channel")
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    messages_received.append(message['data'].decode())
                    if len(messages_received) >= 2:
                        break
            await pubsub.unsubscribe("test_channel")
            await pubsub.close()
        
        async def publisher():
            await asyncio.sleep(0.2)  # Let subscriber connect
            await real_redis.publish("test_channel", "hello")
            await asyncio.sleep(0.1)
            await real_redis.publish("test_channel", "world")
        
        # Run both
        await asyncio.gather(subscriber(), publisher())
        
        assert len(messages_received) == 2
        assert "hello" in messages_received
        assert "world" in messages_received

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_redis_lru_cache(self, real_redis):
        """Test LRU caching pattern with maxmemory policy."""
        cache_key = "test_cache:embeddings"
        
        # Set multiple keys
        for i in range(20):
            await real_redis.hset(cache_key, f"field_{i}", f"value_{i}")
        
        # Set expiration on individual fields not typical; use separate keys instead
        # This test verifies basic cache operations
        count = await real_redis.hlen(cache_key)
        assert count == 20
        
        # Retrieve
        val = await real_redis.hget(cache_key, "field_5")
        assert val == b"value_5"

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_redis_scripts(self, real_redis):
        """Test Lua script execution (used for atomic operations)."""
        # Example: atomic increment with expiry
        script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local ttl = tonumber(ARGV[2])
            
            local count = redis.call('INCR', key)
            if count == 1 then
                redis.call('EXPIRE', key, ttl)
            end
            
            if count > limit then
                return 0  -- Deny
            else
                return 1  -- Allow
            end
        """
        
        key = "test_limiter"
        limit = 5
        ttl = 60
        
        # Load script
        sha = await real_redis.script_load(script)
        
        # Execute multiple times
        results = []
        for _ in range(7):
            allowed = await real_redis.evalsha(sha, 1, key, str(limit), str(ttl))
            results.append(allowed)
        
        # First 5 should be allowed, next 2 denied
        assert results[:5] == [1, 1, 1, 1, 1]
        assert results[5:] == [0, 0]

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_redis_persistence_survives_restart(self, real_redis):
        """Test that Redis persists data across connections (simulated)."""
        test_key = "persistence_test"
        test_value = "survives_reconnect"
        
        await real_redis.set(test_key, test_value)
        
        # Reconnect (create new client)
        import redis.asyncio as redis
        new_client = redis.from_url(str(real_redis.connection_pool.connection_kwargs.get('url', 'redis://localhost:6379')))
        retrieved = await new_client.get(test_key)
        await new_client.close()
        
        assert retrieved.decode() == test_value

    @pytest.mark.redis
    @pytest.mark.integration
    async def test_redis_cluster_ops(self, real_redis):
        """Test cluster-aware operations if using Redis Cluster."""
        # Check if connected to cluster
        info = await real_redis.info()
        cluster_enabled = info.get('cluster_enabled', 0)
        
        if cluster_enabled == 1:
            # Verify cluster state
            cluster_info = await real_redis.cluster_info()
            assert 'cluster_state' in cluster_info
            assert cluster_info['cluster_state'] == 'ok'
        else:
            pytest.skip("Not connected to Redis Cluster - skipping cluster-specific test")
