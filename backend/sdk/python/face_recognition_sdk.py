import requests
import json
from typing import List, Dict, Any, Optional
import base64


class FaceRecognitionSDK:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def enroll_person(self, name: str, images: List[bytes], consent: bool = True,
                      camera_id: str = None, metadata: str = None) -> Dict[str, Any]:
        """Enroll a person with face images"""
        files = [("images", img) for img in images]
        data = {
            "name": name,
            "consent": consent,
            "camera_id": camera_id,
            "metadata": metadata
        }

        response = self.session.post(
            f"{self.base_url}/api/enroll", files=files, data=data)
        response.raise_for_status()
        return response.json()

    def recognize_faces(self, image: bytes, top_k: int = 1, threshold: float = 0.4,
                        camera_id: str = None) -> Dict[str, Any]:
        """Recognize faces in an image"""
        files = {"image": image}
        data = {
            "top_k": top_k,
            "threshold": threshold,
            "camera_id": camera_id
        }

        response = self.session.post(
            f"{self.base_url}/api/recognize", files=files, data=data)
        response.raise_for_status()
        return response.json()

    def get_person(self, person_id: str) -> Dict[str, Any]:
        """Get person details"""
        response = self.session.get(f"{self.base_url}/api/persons/{person_id}")
        response.raise_for_status()
        return response.json()

    def delete_person(self, person_id: str) -> Dict[str, Any]:
        """Delete a person"""
        response = self.session.delete(
            f"{self.base_url}/api/persons/{person_id}")
        response.raise_for_status()
        return response.json()

    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        response = self.session.get(f"{self.base_url}/api/metrics")
        response.raise_for_status()
        return response.json()

    def get_audit_logs(self, limit: int = 100, start_date: str = None,
                       end_date: str = None, action: str = None) -> Dict[str, Any]:
        """Get audit logs"""
        params = {
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date,
            "action": action
        }
        response = self.session.get(
            f"{self.base_url}/api/audit", params=params)
        response.raise_for_status()
        return response.json()
