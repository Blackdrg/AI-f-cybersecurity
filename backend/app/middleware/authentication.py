"""Authentication Middleware - JWT validation with distributed revocation"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError
import logging
import redis.asyncio as redis
from typing import Optional

from backend.app.security import get_encrypted_redis_client

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/health", "/api/health", "/api/version", "/docs", "/openapi.json", "/redoc", "/api/webhooks/stripe", "/api/webhooks/biometric-event"}

class MockRevocationStore:
    """Mock Redis store for tests and degraded operation."""
    def __init__(self):
        self.data = {}
        self._call_log = []
    
    async def ping(self):
        return True
    
    async def setex(self, key, ttl, value):
        # Simulate encryption for consistency
        if isinstance(value, str):
            self.data[key] = value
        else:
            self.data[key] = str(value)
        self._call_log.append(('setex', key, ttl))
    
    async def exists(self, key):
        return 1 if key in self.data else 0
    
    async def get(self, key):
        return self.data.get(key)
    
    async def ttl(self, key):
        if key in self.data:
            # Return remaining TTL (simplified)
            return 3600
        return -2
    
    async def delete(self, key):
        if key in self.data:
            del self.data[key]
    
    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline."""
    def __init__(self, client):
        self.client = client
        self.operations = []
    
    def setex(self, key, ttl, value):
        self.operations.append(('setex', key, ttl, value))
        return self
    
    async def execute(self):
        for op in self.operations:
            if op[0] == 'setex':
                _, key, ttl, value = op
                self.client.data[key] = value
        return [True] * len(self.operations)
    
    def __getattr__(self, name):
        def dummy(*args, **kwargs):
            return self
        return dummy


class DistributedJWTRevocationStore:
    def __init__(self, redis_url=None):
        self.redis_url = redis_url or "redis://localhost:6379"
        self.client = None
        self._initialized = False
        self._mock_mode = self.redis_url in ("redis://mock:6379",)
    
    async def ensure_connected(self):
        if self._initialized or self.client is not None:
            return
        try:
            # Use encrypted Redis client for at-rest encryption
            self.client = await get_encrypted_redis_client(self.redis_url)
            await self.client.ping()
            self._initialized = True
            logger.info("JWT revocation store connected to Redis (encrypted)")
        except Exception as e:
            logger.warning("Redis connection failed: " + str(e))
            self.client = None
      
    async def _ensure_client(self):
        if self._initialized and self.client is not None:
            return
        if self._mock_mode:
            self.client = MockRevocationStore()
            self._initialized = True
            return
        try:
            self.client = await get_encrypted_redis_client(self.redis_url)
            await self.client.ping()
            self._initialized = True
            logger.info("JWT revocation store connected to Redis (encrypted)")
        except Exception as e:
            logger.warning("Redis connection failed: " + str(e) + "; using mock mode.")
            self.client = MockRevocationStore()
            self._initialized = True
    
    async def revoke_token(self, jti, expires_at):
        await self._ensure_client()
        try:
            now = int(time.time())
            ttl = max(1, expires_at - now)
            await self.client.setex("jwt_revoked:" + jti, ttl, str(expires_at))
            logger.info("JWT revoked: " + jti)
            return True
        except Exception as e:
            logger.error("Failed to revoke JWT " + jti + ": " + str(e))
            return False
    
    async def revoke_token_batch(self, jtis, expires_at):
        await self._ensure_client()
        try:
            now = int(time.time())
            ttl = max(1, expires_at - now)
            pipe = self.client.pipeline()
            for jti in jtis:
                pipe.setex("jwt_revoked:" + jti, ttl, str(expires_at))
            await pipe.execute()
            return {"success": True, "revoked": len(jtis)}
        except Exception as e:
            logger.error("Batch revocation failed: " + str(e))
            return {"success": False, "revoked": 0}
    
    async def is_revoked(self, jti):
        if not self._initialized or self.client is None:
            return False
        try:
            result = await self.client.exists("jwt_revoked:" + jti)
            return bool(result)
        except Exception as e:
            logger.error("Failed to check revocation: " + str(e))
            return False
    
    async def get_revocation_info(self, jti):
        if not self._initialized or self.client is None:
            return None
        try:
            value = await self.client.get("jwt_revoked:" + jti)
            if value:
                ttl = await self.client.ttl("jwt_revoked:" + jti)
                return {"jti": jti, "revoked": True, "expires_at": int(value) if value else None, "ttl_remaining": ttl}
            return None
        except Exception as e:
            logger.error("Failed to get revocation info: " + str(e))
            return None


_jwt_revocation_store = None

def get_jwt_revocation_store():
    global _jwt_revocation_store
    if _jwt_revocation_store is None:
        _jwt_revocation_store = DistributedJWTRevocationStore()
    return _jwt_revocation_store


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key, algorithm="HS256"):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    async def dispatch(self, request, call_next):
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"success": False, "error": "Missing or invalid authorization header"})
        token = auth_header.split(" ")[1]
        local_jti = None
        try:
            unverified = jwt.decode(token, None, options={"verify_signature": False}, algorithms=[self.algorithm])
            local_jti = unverified.get("jti")
            if local_jti:
                revocation_store = get_jwt_revocation_store()
                await revocation_store.ensure_connected()
                if await revocation_store.is_revoked(local_jti):
                    return JSONResponse(status_code=401, content={"success": False, "error": "Token has been revoked", "code": "TOKEN_REVOKED"})
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_signature": True, "verify_exp": True, "verify_nbf": True})
            user_id = payload.get("user_id")
            if not user_id:
                raise JWTError("Missing user_id")
            request.state.user_id = user_id
            request.state.user_role = payload.get("role", "viewer")
            request.state.org_id = payload.get("org_id")
            request.state.org_tier = payload.get("subscription_tier", "free")
            request.state.authenticated = True
            request.state.token_jti = local_jti
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"success": False, "error": "Token has expired", "code": "TOKEN_EXPIRED"})
        except JWTError as e:
            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid or expired token"})
        except Exception as e:
            logger.error(f"Auth middleware exception: {type(e).__name__}: {e}")
            return JSONResponse(status_code=500, content={"success": False, "error": "Auth service unavailable", "code": "AUTH_SERVICE_ERROR"})
        response = await call_next(request)
        return response