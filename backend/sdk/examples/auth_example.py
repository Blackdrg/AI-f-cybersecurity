import asyncio
import httpx
import sys
import os

# Add SDK path to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from python.sdk import AIFaceSDK

async def run_e2e_example():
    """
    End-to-End Authentication and Recognition Example.
    1. Login to get JWT
    2. Initialize SDK
    3. Perform recognition
    """
    base_url = "http://localhost:8000"
    email = "admin@example.com"
    password = "password" # In reality, fetched from env
    
    print(f"[*] Authenticating as {email}...")
    
    async with httpx.AsyncClient() as client:
        # 1. Login
        login_res = await client.post(
            f"{base_url}/api/auth/login?email={email}&password={password}"
        )
        
        if login_res.status_code != 200:
            print(f"[!] Login failed: {login_res.text}")
            return
            
        auth_data = login_res.json()
        token = auth_data["access_token"]
        user = auth_data["user"]
        
        print(f"[+] Login successful. Welcome {user['name']} ({user['role']})")
        
        # 2. Initialize SDK
        sdk = AIFaceSDK(base_url, token)
        
        # 3. Perform a health check
        health = await client.get(f"{base_url}/api/health", headers={"Authorization": f"Bearer {token}"})
        print(f"[*] System Health: {health.json()['data']['status']}")
        
        # 4. (Optional) Run recognition
        # with open("test_face.jpg", "rb") as f:
        #    result = await sdk.recognize(f.read())
        #    print(f"[*] Recognition Result: {result}")

if __name__ == "__main__":
    asyncio.run(run_e2e_example())
