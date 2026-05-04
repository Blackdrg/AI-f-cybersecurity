import os
import logging
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..security import verify_token, create_token
from .authentication import DistributedJWTRevocationStore

logger = logging.getLogger(__name__)


class SecureCookieAuthMiddleware(BaseHTTPMiddleware):
    """Replace localStorage JWT with httpOnly Secure cookies."""
    
    def __init__(self, app):
        super().__init__(app)
        self.revocation_store = DistributedJWTRevocationStore()
        self.cookie_name = "aif_session"
        self.cookie_flags = "HttpOnly; Secure; SameSite=Strict; Path=/"
    
    async def dispatch(self, request: Request, call_next: Callable):
        user = await self.get_current_user(request)
        if user:
            request.state.user = user
        response = await call_next(request)
        return response
    
    async def get_current_user(self, request: Request) -> Optional[dict]:
        """Extract user from httpOnly cookie, verify JWT + revocation."""
        cookie = request.cookies.get(self.cookie_name)
        if not cookie:
            return None
        
        try:
            payload = verify_token(cookie)
            jti = payload.get("jti")
            
            if await self.revocation_store.is_revoked(jti):
                logger.warning(f"Revoked token JTI: {jti}")
                return None
            
            return payload
        except Exception:
            return None
    
    async def set_auth_cookie(self, response: Response, user_id: str, role: str = "user") -> str:
        """Set secure httpOnly cookie w/ fresh JWT."""
        token = create_token(user_id, role)
        max_age = 24*60*60
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            httponly=True,
            secure=os.getenv("ENV_PROD", "false") == "true",
            samesite="strict",
            max_age=max_age,
            path="/"
        )
        return token


def get_current_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
