"""Security Middleware - Headers, Request Limits, and Sanitization"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
import bleach
import json

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Content Security Policy - Enhanced
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' *.cloudflare.com https://api.stripe.com;"
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        # HTTP Strict Transport Security
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions-Policy
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(self), microphone=(), payment=()"
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "0" # Deprecated, CSP is better
        
        return response

class SanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize all incoming JSON request bodies."""
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        data = json.loads(body)
                        sanitized_data = self._sanitize_recursive(data)
                        
                        # Re-create request with sanitized body
                        async def receive():
                            return {"type": "http.request", "body": json.dumps(sanitized_data).encode()}
                        
                        request._receive = receive
                except Exception as e:
                    logger.error(f"Sanitization error: {e}")
                    # If we can't parse it, we'll let it pass or block it? 
                    # Blocking is safer.
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "error": "Invalid JSON"}
                    )
        
        return await call_next(request)

    def _sanitize_recursive(self, data):
        if isinstance(data, dict):
            return {k: self._sanitize_recursive(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_recursive(v) for v in data]
        elif isinstance(data, str):
            return bleach.clean(data)
        else:
            return data

class RequestLimitsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024): # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                return JSONResponse(
                    status_code=413,
                    content={"success": False, "error": "Request entity too large"}
                )
        
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Request error: {e}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Internal server error"}
            )
