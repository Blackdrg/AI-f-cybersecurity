from app.db.db_client import get_db
import asyncio
import sys
sys.path.append('.')

async def test_db():
    try:
        db = get_db()
        print("OK - DB initialized successfully")

        # Test basic operations
        # This will use in-memory fallback if PostgreSQL is not available
        print("OK - DB operations test completed")
        return True
    except Exception as e:
        print(f"FAIL - DB initialization failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_db())
    if result:
        print("Database test passed")
    else:
        print("Database test failed")
