import requests
import json
from typing import List, Dict, Optional

class AIFClient:
    """
    Official Python SDK for AI-f Enterprise Face Recognition.
    """
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def recognize(self, image_path: str, top_k: int = 1) -> Dict:
        """Perform face recognition on an image file."""
        url = f"{self.base_url}/api/recognize"
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'top_k': top_k}
            response = requests.post(url, headers={"Authorization": self.headers["Authorization"]}, files=files, data=data)
        return response.json()

    def enroll(self, name: str, images: List[str]) -> Dict:
        """Enroll a new person with multiple images."""
        url = f"{self.base_url}/api/enroll"
        # Implementation for multiple images
        return {}

    def get_health(self) -> Dict:
        """Check system health."""
        return requests.get(f"{self.base_url}/api/health", headers=self.headers).json()
