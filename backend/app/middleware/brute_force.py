import time
import asyncio
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from ..services.redis_client import get_redis
import logging

logger = logging.getLogger(__name__)

class BruteForceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect against brute-force attacks on login/auth endpoints.
    Uses Redis to track failed attempts and applies exponential back-off.
    """
    def __init__(self, app, max_attempts: int = 5, initial_backoff: int = 2):
        super().__init__(app)
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in ["/api/auth/login", "/api/v1/auth/login"]:
            redis = get_redis()
            if not redis:
                return await call_next(request)

            # Use IP or user identifier if available (email is in body, which we shouldn't read here)
            # For now, let's use IP address
            client_ip = request.client.host if request.client else "unknown"
            key = f"brute_force:{client_ip}"
            
            attempts = await redis.get(key)
            attempts = int(attempts) if attempts else 0

            if attempts >= self.max_attempts:
                backoff_time = self.initial_backoff ** (attempts - self.max_attempts + 1)
                backoff_time = min(backoff_time, 3600) # Max 1 hour
                
                logger.warning(f"Brute-force detected from IP {client_ip}. Attempts: {attempts}. Backoff: {backoff_time}s")
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False, 
                        "error": "Too many failed attempts. Please try again later.",
                        "retry_after": backoff_time
                    },
                    headers={"Retry-After": str(backoff_time)}
                )

        response = await call_next(request)

        # After the request, if it was a login attempt and it failed (401), increment attempts
        if request.method == "POST" and request.url.path in ["/api/auth/login", "/api/v1/auth/login"]:
            if response.status_code == 401:
                redis = get_redis()
                if redis:
                    client_ip = request.client.host if request.client else "unknown"
                    key = f"brute_force:{client_ip}"
                    await redis.incr(key)
                    await redis.expire(key, 300) # Reset after 5 minutes of no activity
            elif response.status_code == 200:
                # Reset on success
                redis = get_redis()
                if redis:
                    client_ip = request.client.host if request.client else "unknown"
                    key = f"brute_force:{client_ip}"
                    await redis.delete(key)

        return response
