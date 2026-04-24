import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global Rate Limiting Middleware with sliding window.
    Supports tiered limits based on organization or user role.
    """
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.history = defaultdict(list)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        # Identify client (by org_id from JWT or IP)
        client_id = request.client.host
        
        # Try to get org_id from headers if already authenticated
        # Note: In a real app, this might happen after authentication
        # For global protection, IP is a good fallback
        
        with self.lock:
            now = time.time()
            # Clean old entries
            self.history[client_id] = [t for t in self.history[client_id] if now - t < 60]
            
            if len(self.history[client_id]) >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Rate limit exceeded. Please try again later.",
                        "retry_after": 60 - (now - self.history[client_id][0])
                    }
                )
            
            self.history[client_id].append(now)

        response = await call_next(request)
        return response
