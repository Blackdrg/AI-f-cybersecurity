"""
AI-f Python HTTP SDK

A simple, full-featured Python client for the AI-f REST API.
This SDK provides a clean interface to all REST endpoints.

Installation:
    pip install aif-python

Usage:
    from aif import AIFClient
    
    client = AIFClient(base_url="http://localhost:8000")
    
    # Login
    client.login("demo@example.com", "password")
    
    # Enroll
    result = client.enroll(name="John Doe", images=["photo1.jpg"])
    
    # Recognize
    result = client.recognize(image="query.jpg")

"""

import base64
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class Person:
    person_id: str
    name: str
    org_id: str
    created_at: str
    consent_given: bool
    metadata: Dict[str, Any]


@dataclass
class RecognitionResult:
    faces: List[Dict[str, Any]]
    processing_time_ms: int
    request_id: str


class AIFClient:
    """
    Python client for AI-f Face Recognition REST API.
    
    Usage:
        client = AIFClient(base_url="http://localhost:8000")
        client.login("demo@example.com", "password")
        result = client.recognize(image="photo.jpg")
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.org_id: Optional[str] = None
        self._session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        self._session.headers.update({"Content-Type": "application/json"})
    
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request to API."""
        url = f"{self.base_url}{path}"
        
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = self._session.request(
            method,
            url,
            headers=headers,
            timeout=kwargs.pop("timeout", 30),
            **kwargs
        )
        
        # Handle common errors
        if response.status_code == 401:
            raise AIFAuthenticationError("Authentication failed. Please login again.")
        if response.status_code == 429:
            raise AIFRateLimitError("Rate limit exceeded")
        
        response.raise_for_status()
        return response
    
    def _parse_response(self, response: requests.Response) -> Any:
        """Parse API response envelope."""
        data = response.json()
        
        if not data.get("success", True):
            error = data.get("error", "Unknown error")
            raise AIFAPIError(error, data.get("error_code"))
        
        return data.get("data", data)
    
    # ==================
    # Authentication
    # ==================
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and get access token.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict with access_token, refresh_token, expires_in
        """
        response = self._request(
            "POST",
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        data = self._parse_response(response)
        
        self.token = data.get("access_token")
        return data
    
    def login_with_api_key(self, api_key: str) -> None:
        """
        Authenticate using API key.
        
        Args:
            api_key: Your API key from dashboard
        """
        self.token = api_key
    
    def logout(self) -> None:
        """Clear authentication tokens."""
        if self.token:
            try:
                self._request("POST", "/api/auth/logout")
            except Exception:
                pass
        self.token = None
        self.user_id = None
        self.org_id = None
    
    def refresh_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.token:
            raise AIFAuthenticationError("Not authenticated")
        
        response = self._request("POST", "/api/auth/refresh")
        data = self._parse_response(response)
        self.token = data.get("access_token")
        return data
    
    # ==================
    # Health
    # ==================
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        response = self._request("GET", "/health")
        return response.json()
    
    def detailed_health(self) -> Dict[str, Any]:
        """Check detailed health with dependencies."""
        response = self._request("GET", "/api/health")
        return self._parse_response(response)
    
    # ==================
    # Core Recognition
    # ==================
    
    def enroll(
        self,
        name: str,
        images: List[str],
        consent: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        metadata_json: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enroll a new person in the system.
        
        Args:
            name: Person's name
            images: List of image file paths (.jpg, .png)
            consent: Consent flag (required)
            metadata: Optional metadata dict
            metadata_json: Optional metadata as JSON string
            
        Returns:
            Dict with person_id, message
        """
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        if not consent:
            raise AIFAPIError("Consent is required", "CONSENT_REQUIRED")
        
        files = []
        for i, img_path in enumerate(images):
            if not os.path.exists(img_path):
                raise AIFAPIError(f"Image not found: {img_path}")
            files.append
            ("images", (os.path.basename(img_path), open(img_path, "rb"), "image/jpeg")
            )
        
        try:
            data = {"name": name, "consent": str(consent)}
            if metadata:
                data["metadata"] = str(metadata)
            elif metadata_json:
                data["metadata"] = metadata_json
            
            response = self._session.request(
                "POST",
                f"{self.base_url}/api/enroll",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 401:
                raise AIFAuthenticationError("Authentication failed")
            response.raise_for_status()
            return self._parse_response(response)
            
        finally:
            for _, f, _, _ in files:
                f.close()
    
    def recognize(
        self,
        image: str,
        top_k: int = 5,
        threshold: float = 0.7,
        enable_spoof_check: bool = True,
        camera_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recognize a face in an image.
        
        Args:
            image: Image file path
            top_k: Number of top matches to return
            threshold: Confidence threshold (0-1)
            enable_spoof_check: Enable anti-spoof detection
            camera_id: Camera identifier
            
        Returns:
            Dict with faces, matches, processing_time_ms
        """
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        if not os.path.exists(image):
            raise AIFAPIError(f"Image not found: {image}")
        
        with open(image, "rb") as f:
            files = {"image": (os.path.basename(image), f, "image/jpeg")}
            data = {
                "top_k": str(top_k),
                "threshold": str(threshold),
                "enable_spoof_check": str(enable_spoof_check).lower()
            }
            if camera_id:
                data["camera_id"] = camera_id
            
            response = self._session.request(
                "POST",
                f"{self.base_url}/api/recognize",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 401:
                raise AIFAuthenticationError("Authentication failed")
            response.raise_for_status()
            return self._parse_response(response)
    
    def recognize_base64(
        self,
        image_base64: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Recognize face from base64 encoded image.
        
        Args:
            image_base64: Base64 encoded image
            top_k: Number of matches
            threshold: Confidence threshold
            
        Returns:
            Dict with recognition results
        """
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request(
            "POST",
            "/api/recognize",
            json={
                "image": image_base64,
                "top_k": top_k,
                "threshold": threshold
            }
        )
        return self._parse_response(response)
    
    # ==================
    # Person Management
    # ==================
    
    def list_persons(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List enrolled persons."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request(
            "GET",
            f"/api/persons?limit={limit}&offset={offset}"
        )
        return self._parse_response(response)
    
    def get_person(self, person_id: str) -> Person:
        """Get person details."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("GET", f"/api/persons/{person_id}")
        data = self._parse_response(response)
        return Person(**data)
    
    def update_person(
        self,
        person_id: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Update person details."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        json_data = {}
        if name:
            json_data["name"] = name
        if metadata:
            json_data["metadata"] = metadata
        
        response = self._request(
            "PUT",
            f"/api/persons/{person_id}",
            json=json_data
        )
        return self._parse_response(response)
    
    def delete_person(self, person_id: str) -> Dict[str, Any]:
        """Delete person."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("DELETE", f"/api/persons/{person_id}")
        return self._parse_response(response)
    
    # ==================
    # Analytics
    # ==================
    
    def get_analytics(
        self,
        timeframe: str = "24h"
    ) -> Dict[str, Any]:
        """Get analytics for timeframe."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request(
            "GET",
            f"/api/analytics?timeframe={timeframe}"
        )
        return self._parse_response(response)
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get risk metrics."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("GET", "/api/analytics/risk-metrics")
        return self._parse_response(response)
    
    # ==================
    # Admin
    # ==================
    
    def list_api_keys(self) -> Dict[str, Any]:
        """List your API keys."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("GET", "/api/keys")
        return self._parse_response(response)
    
    def create_api_key(self, name: str) -> Dict[str, Any]:
        """Create a new API key."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request(
            "POST",
            "/api/keys",
            json={"name": name}
        )
        return self._parse_response(response)
    
    def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        """Revoke an API key."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("DELETE", f"/api/keys/{key_id}")
        return self._parse_response(response)
    
    def list_organizations(self) -> Dict[str, Any]:
        """List organizations."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("GET", "/api/organizations")
        return self._parse_response(response)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        if not self.token:
            raise AIFAuthenticationError("Authentication required")
        
        response = self._request("GET", "/api/admin/systems/status")
        return self._parse_response(response)
    
    # ==================
    # WebSocket (Real-time)
    # ==================
    
    def get_websocket_url(self, path: str = "/ws/recognize_stream") -> str:
        """Get WebSocket URL."""
        # Convert http(s) to ws(s)
        if self.base_url.startswith("https"):
            return self.base_url.replace("https", "wss") + path
        return self.base_url.replace("http", "ws") + path
    
    # ==================
    # Context Manager
    # ==================
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()
    
    def close(self):
        """Close client and clear session."""
        self.logout()
        self._session.close()


# ==================
# Exceptions
# ==================

class AIFError(Exception):
    """Base exception for AI-f SDK."""
    pass

class AIFAuthenticationError(AIFError):
    """Authentication failed."""
    pass

class AIFAPIError(AIFError):
    """API returned an error."""
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.code = code

class AIFRateLimitError(AIFError):
    """Rate limit exceeded."""
    pass


# ==================
# Convenience Functions
# ==================

def enroll_from_directory(
    directory: str,
    name: str,
    base_url: str = "http://localhost:8000",
    email: str = "demo@example.com",
    password: str = "password"
) -> Dict[str, Any]:
    """
    Convenience function to enroll all images from a directory.
    
    Args:
        directory: Directory containing images
        name: Person's name
        base_url: API base URL
        email: Login email
        password: Login password
        
    Returns:
        Enrollment result
    """
    # Find all images in directory
    extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    images = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.splitext(f.lower())[1] in extensions
    ]
    
    if not images:
        raise AIFError(f"No images found in {directory}")
    
    # Create client and enroll
    with AIFClient(base_url) as client:
        client.login(email, password)
        return client.enroll(name=name, images=images, consent=True)


def recognize_cropped_image(
    image_path: str,
    person_name: str,
    base_url: str = "http://localhost:8000",
    email: str = "demo@example.com",
    password: str = "password"
) -> Dict[str, Any]:
    """
    Recognize face and check if it matches a specific person.
    
    Args:
        image_path: Path to image
        person_name: Expected person's name
        base_url: API base URL
        email: Login email
        password: Login password
        
    Returns:
        Recognition result
    """
    with AIFClient(base_url) as client:
        client.login(email, password)
        result = client.recognize(image=image_path)
        
        # Check if matched person
        if result.get("faces"):
            for face in result["faces"]:
                for match in face.get("matches", []):
                    if match.get("name", "").lower() == person_name.lower():
                        return {"matched": True, "confidence": match["confidence"]}
        
        return {"matched": False}


# ==================
# Main
# ==================

if __name__ == "__main__":
    import sys
    
    # Simple demo
    print("AI-f Python HTTP SDK")
    print("=" * 40)
    
    # Check health
    try:
        client = AIFClient()
        health = client.health_check()
        print(f"Health: {health}")
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)
    
    # Login
    try:
        client.login("demo@example.com", "password")
        print("Login: OK")
    except Exception as e:
        print(f"Login failed: {e}")
    
    # List persons
    try:
        persons = client.list_persons()
        print(f"Persons: {len(persons.get('persons', []))}")
    except Exception as e:
        print(f"List persons failed: {e}")
