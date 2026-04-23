"""
Global exception handlers for FastAPI application.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback
import uuid
from typing import Any, Dict

logger = logging.getLogger("face-recognition.exceptions")


class FaceRecognitionException(Exception):
    """Base exception for face recognition errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ModelLoadException(FaceRecognitionException):
    """Raised when ML model fails to load."""
    def __init__(self, message: str = "Model loading failed"):
        super().__init__(message, code="MODEL_LOAD_ERROR", status_code=503)


class RecognitionException(FaceRecognitionException):
    """Raised when face recognition fails."""
    def __init__(self, message: str = "Recognition failed"):
        super().__init__(message, code="RECOGNITION_ERROR", status_code=500)


class DatabaseException(FaceRecognitionException):
    """Raised when database operation fails."""
    def __init__(self, message: str = "Database error"):
        super().__init__(message, code="DATABASE_ERROR", status_code=500)


class ValidationException(FaceRecognitionException):
    """Raised when input validation fails."""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class AuthenticationException(FaceRecognitionException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code="AUTH_ERROR", status_code=401)


class AuthorizationException(FaceRecognitionException):
    """Raised when user lacks permission."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTH_ERROR", status_code=403)


class RateLimitExceeded(FaceRecognitionException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code="RATE_LIMIT_ERROR", status_code=429)


class CameraOfflineException(FaceRecognitionException):
    """Raised when camera is offline."""
    def __init__(self, message: str = "Camera is offline"):
        super().__init__(message, code="CAMERA_OFFLINE", status_code=503)


class EnrollmentException(FaceRecognitionException):
    """Raised when enrollment fails."""
    def __init__(self, message: str = "Enrollment failed"):
        super().__init__(message, code="ENROLLMENT_ERROR", status_code=400)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler that catches all unhandled exceptions
    and returns a consistent JSON error response with request ID for tracing.
    """
    request_id = str(uuid.uuid4())

    if isinstance(exc, FaceRecognitionException):
        # Known application exception
        logger.error(
            f"Application error [{request_id}]: {exc.message}",
            extra={
                "request_id": request_id,
                "code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                }
            }
        )

    elif isinstance(exc, HTTPException):
        # FastAPI HTTPException
        logger.warning(
            f"HTTP {exc.status_code} [{request_id}]: {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "request_id": request_id,
                }
            }
        )

    elif isinstance(exc, RequestValidationError):
        # Pydantic validation error
        logger.warning(
            f"Validation error [{request_id}]: {exc.errors()}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
            }
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "details": exc.errors(),
                    "request_id": request_id,
                }
            }
        )

    else:
        # Unexpected unhandled exception
        logger.error(
            f"Unhandled exception [{request_id}]: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please contact support with the request ID.",
                    "request_id": request_id,
                }
            }
        )


def setup_exception_handlers(app):
    """Register exception handlers with the FastAPI app."""
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(RequestValidationError, global_exception_handler)
    app.add_exception_handler(HTTPException, global_exception_handler)
