"""
Authentication Middleware
Validates JWT on all routes (except excluded) and sets user context for downstream middleware.
"""
import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError
import logging
import re
from app.models.revocable_tokens import is_token_revoked, get_token_revocation_info

logger = logging.getLogger(__name__)

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health", "/api/health", "/api/version",
    "/docs", "/openapi.json", "/redoc",
    "/api/enroll",  # Enrollment is public (without auth but requires consent etc handled in endpoint)
    "/api/recognize",  # Recognition is public? The README says all /api/* except enroll/recognize require auth. Actually those two are public.
}

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Validates JWT and attaches user info to request.state.
    Must be placed BEFORE RateLimitMiddleware, AFTER any CORS/TrustedHost.
    """
    
    def __init__(self, app, secret_key: str, algorithm: str = "HS256"):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    async def dispatch(self, request: Request, call_next):
        # Skip public paths
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Missing or invalid authorization header"}
            )
        
        token = auth_header.split(" ")[1]
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            role = payload.get("role", "user")
            org_id = payload.get("org_id")
            subscription_tier = payload.get("subscription_tier", "free")
            jti = payload.get("jti")  # JWT token ID for revocation
            
            if not user_id:
                raise JWTError("Missing user_id")
            
            # Attach user context to request state
            request.state.user_id = user_id
            request.state.user_role = role
            request.state.org_id = org_id
            request.state.org_tier = subscription_tier
            request.state.authenticated = True
            request.state.token_jti = jti
            
            # Attach request metadata for policy engine
            request.state.client_ip = request.client.host if request.client else None
            request.state.user_agent = request.headers.get("user-agent", "")
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Invalid or expired token"}
            )
        
        response = await call_next(request)
        return response
