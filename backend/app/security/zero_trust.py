import jwt
import time
import os
from typing import Optional
from .secrets_manager import secrets_manager

class ZeroTrustAuth:
    """
    Implements Zero Trust authentication for internal services.
    Every service-to-service call must be authenticated via a short-lived JWT.
    """
    def __init__(self):
        self.service_secret = secrets_manager.get_secret("INTERNAL_SERVICE_SECRET", "internal_secret")

    def generate_service_token(self, service_name: str) -> str:
        """Generates a short-lived (5 min) JWT for internal service authentication."""
        payload = {
            "iss": "ai-f-core",
            "sub": service_name,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "internal": True
        }
        return jwt.encode(payload, self.service_secret, algorithm="HS256")

    def verify_service_token(self, token: str) -> bool:
        """Verifies if the token is a valid internal service token."""
        try:
            payload = jwt.decode(token, self.service_secret, algorithms=["HS256"])
            return payload.get("internal") is True
        except Exception:
            return False

zero_trust = ZeroTrustAuth()
