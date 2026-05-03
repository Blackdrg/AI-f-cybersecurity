"""Redis client for AI-f."""
import redis.asyncio as redis
import os

async def get_redis():
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = redis.from_url(url, decode_responses=True)
    try:
        await r.ping()
        return r
    except:
        raise Exception("Redis unavailable - start Redis docker-compose service")

