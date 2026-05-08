
import asyncio
import asyncpg
import os

async def check_db():
    try:
        # Try default from .env
        conn = await asyncpg.connect(
            user='postgres',
            password='postgres_secure_password_123!',
            database='face_recognition',
            host='localhost',
            port=5432
        )
        print("Successfully connected to localhost:5432 with password from .env")
        await conn.close()
    except Exception as e:
        print(f"Failed to connect to localhost:5432: {e}")

    for pwd in ['postgres_secure_password_123!', 'password', 'postgres']:
        try:
            conn = await asyncpg.connect(
                user='postgres',
                password=pwd,
                database='face_recognition_test', # Integration tests usually use _test
                host='localhost',
                port=5433
            )
            print(f"Successfully connected to localhost:5433 with password: {pwd}")
            await conn.close()
            break
        except Exception as e:
            print(f"Failed to connect to localhost:5433 with password {pwd}: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
