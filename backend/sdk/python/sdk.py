import httpx
import asyncio
from typing import List, Optional, Dict, Any

class AIFaceSDK:
    """
    AI-f Sovereign OS Python SDK
    Provides a high-level async interface for face recognition and identity management.
    """
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "X-SDK-Version": "1.0.0"
        }

    async def enroll(self, name: str, images: List[bytes], consent: bool = True, metadata: Dict[str, Any] = None):
        """Enroll a new identity."""
        async with httpx.AsyncClient() as client:
            files = [("images", img) for img in images]
            data = {
                "name": name,
                "consent": str(consent).lower(),
                "metadata": (None, str(metadata or {}))
            }
            response = await client.post(
                f"{self.base_url}/api/enroll",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()

    async def recognize(self, image: bytes, top_k: int = 5, threshold: float = 0.4):
        """Recognize an identity from an image."""
        async with httpx.AsyncClient() as client:
            files = {"image": image}
            data = {
                "top_k": str(top_k),
                "threshold": str(threshold)
            }
            response = await client.post(
                f"{self.base_url}/api/recognize",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()

    async def get_identities(self, limit: int = 10, offset: int = 0):
        """List all identities (paginated)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/identities?limit={limit}&offset={offset}",
                headers=self.headers
            )
            return response.json()

# Example Usage:
# async def main():
#     sdk = AIFaceSDK("https://api.ai-f.security", "YOUR_JWT_TOKEN")
#     result = await sdk.recognize(open("face.jpg", "rb").read())
#     print(result)
