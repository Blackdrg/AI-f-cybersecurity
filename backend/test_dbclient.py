import sys
sys.path.insert(0, '.')
import asyncio
from app.db.db_client import DBClient

async def test():
    db = DBClient()
    await db.init_db()
    print('pool:', db.pool)
    if db.pool:
        print('DB OK')
        await db.close()

asyncio.run(test())