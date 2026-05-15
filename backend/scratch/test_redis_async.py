import asyncio
import redis.asyncio as redis

async def test():
    client = redis.from_url("redis://localhost")
    print(f"Client type: {type(client)}")
    print(f"Eval is coroutine: {asyncio.iscoroutinefunction(client.eval)}")
    await client.close()

if __name__ == "__main__":
    asyncio.run(test())
