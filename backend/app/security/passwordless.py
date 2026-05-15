"""
Passwordless Authentication Service.

Handles Magic Link generation and verification.
"""
import os
import secrets
import time
import logging
from typing import Optional, Tuple
from ..db.db_client import get_db
from ..security import create_token
from ..services.redis_client import redis_client

logger = logging.getLogger(__name__)

class PasswordlessAuth:
    """Manages magic link generation and validation."""
    
    def __init__(self):
        self.token_expiry = int(os.getenv("MAGIC_LINK_EXPIRY", "900")) # 15 minutes
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
    async def generate_magic_link(self, email: str) -> str:
        """
        Generate a unique magic link for a user.
        
        Stores the token in Redis for fast verification.
        """
        token = secrets.token_urlsafe(32)
        key = f"magic_link:{token}"
        
        # Store email in Redis with expiry
        await redis_client.set(key, email, ex=self.token_expiry)
        
        magic_link = f"{self.frontend_url}/auth/magic-link?token={token}"
        logger.info(f"Generated magic link for {email}")
        
        # In a real app, you would send this via email
        # send_email(email, "Your AI-f Login Link", f"Click here to login: {magic_link}")
        
        return magic_link

    async def verify_magic_link(self, token: str) -> Optional[str]:
        """
        Verify the magic link token.
        
        Returns the email if valid and not expired.
        """
        key = f"magic_link:{token}"
        email = await redis_client.get(key)
        
        if not email:
            return None
        
        # Consume the token (delete after use)
        await redis_client.delete(key)
        
        return email.decode() if isinstance(email, bytes) else email

passwordless_auth = PasswordlessAuth()
