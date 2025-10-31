import asyncio
from app.aggregator import ResultAggregator


async def test():
    a = ResultAggregator()
    results, calls = await a.enrich('John Doe', ['mock'], 5)
    print(f'Results: {len(results)}')
    for r in results:
        print(f'- {r["title"]}: {r["snippet"][:50]}...')
    print(f'Provider calls: {calls}')

asyncio.run(test())
