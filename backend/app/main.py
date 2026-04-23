"""
Face Recognition Service - Main Application Entry Point
Enhanced with structured logging, validation, and global exception handling.
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import asyncio
import time
import os
import uuid

# Setup structured logging first
from app.logging_config import setup_structured_logging, get_logger
setup_structured_logging()
logger = get_logger(__name__)

# Import exception handlers
from app.exceptions import setup_exception_handlers, ModelLoadException, CameraOfflineException

# Import core modules with lazy loading handled in routers
from .api import enroll, recognize, video_recognize, stream_recognize, admin, federated_learning
from .api import orgs, cameras, events, alerts, analytics, logs, access
from .api import users, plans, subscriptions, payments, usage, ai_assistant, support
from .grpc.server import serve_grpc
from .security import setup_security
from .metrics import setup_metrics
from .db.db_client import init_db

# Request ID middleware
class RequestIDMiddleware:
    """Middleware to add unique request ID to each request."""
    
    async def __call__(self, request: Request, call_next):
        request_id = str(uuid.uuid4()) or request.headers.get("X-Request-ID")
        request.state.request_id = request_id
        
        # Set request ID in context for logging
        logger.set_context(request_id=request_id, method=request.method, path=request.url.path)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.clear_context()


# Application settings validation using Pydantic V2 (BaseSettings deprecated in V2, using pydantic-settings)
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import secrets

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=True,
        env_prefix=''
    )
    """Application settings with validation."""
    
    # Database
    DB_HOST: str = Field(..., default="postgres")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(..., default="postgres")
    DB_PASSWORD: str = Field(..., default="password")
    DB_NAME: str = Field(default="face_recognition")
    
    # JWT & Security
    JWT_SECRET: str = Field(..., min_length=32)
    ENCRYPTION_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Redis
    REDIS_URL: str = Field(default="redis://redis:6379")
    
    # Frontend
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW: int = Field(default=60)  # seconds
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/1")
    
    # Monitoring
    SENTRY_DSN: str = Field(default="")
    PROMETHEUS_ENABLED: bool = Field(default=True)
    
    # Provider API Keys
    STRIPE_SECRET_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    AWS_REGION: str = Field(default="us-east-1")
    KMS_KEY_ID: str = Field(default="alias/face-recognition-key")
    
    # GPU/Model
    USE_GPU: bool = Field(default=False)
    MODEL_CONFIDENCE_THRESHOLD: float = Field(default=0.6)
    ANTI_SPOOFING_ENABLED: bool = Field(default=True)


# Initialize settings
try:
    settings = Settings()
    logger.info("Settings loaded successfully", extra={"settings": settings.model_dump()})
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    raise

# Create FastAPI app with detailed docs
app = FastAPI(
    title="Face Recognition Service",
    version="2.0.0",
    description="Production-ready face recognition system with enrollment, recognition, and multi-tenancy",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware stack (order matters)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Exception handlers
setup_exception_handlers(app)

# Security and metrics setup
setup_security(app)
setup_metrics(app)

# Initialize Celery app
from app.celery_app import app as celery_app

# Make celery app available for import
def get_celery_app():
    return celery_app

# All routers
app.include_router(enroll.router, prefix="/api", tags=["enroll"])
app.include_router(recognize.router, prefix="/api", tags=["recognize"])
app.include_router(video_recognize.router, prefix="/api", tags=["video_recognize"])
app.include_router(stream_recognize.router, prefix="/ws", tags=["stream_recognize"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(federated_learning.router, prefix="/api", tags=["federated_learning"])

# All feature routers
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(plans.router, prefix="/api", tags=["plans"])
app.include_router(subscriptions.router, prefix="/api", tags=["subscriptions"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(usage.router, prefix="/api", tags=["usage"])
app.include_router(ai_assistant.router, prefix="/api", tags=["ai_assistant"])
app.include_router(support.router, prefix="/api", tags=["support"])
app.include_router(public_enrich.router, prefix="/api", tags=["public_enrich"])

# Core routers
app.include_router(orgs.router, prefix="/api", tags=["orgs"])
app.include_router(cameras.router, prefix="/api/orgs", tags=["cameras"])
app.include_router(events.router, prefix="/api/orgs", tags=["events"])
app.include_router(alerts.router, prefix="/api/orgs", tags=["alerts"])
app.include_router(analytics.router, prefix="/api/orgs", tags=["analytics"])
app.include_router(logs.router, prefix="/api/orgs", tags=["logs"])
app.include_router(access.router, prefix="/api/orgs", tags=["access"])

# Legal and recognition v2
from .api.legal import router as legal_router
app.include_router(legal_router, prefix="/api", tags=["legal"])

from .api.recognition_v2 import router as recognition_v2_router
app.include_router(recognition_v2_router, prefix="/api", tags=["recognition_v2"])


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Face Recognition Service...", extra={
        "version": app.version,
        "gpu_enabled": settings.USE_GPU,
        "confidence_threshold": settings.MODEL_CONFIDENCE_THRESHOLD,
    })
    
    try:
        # Initialize database with retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await init_db()
                logger.info("Database initialized successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Database init attempt {attempt + 1} failed, retrying in {wait_time}s", extra={"error": str(e)})
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Database initialization failed after all retries", extra={"error": str(e)})
                    raise ModelLoadException("Database initialization failed")
        
        # Model warmup
        logger.info("Warming up ML models...")
        # TODO: Add actual model warmup logic
        logger.info("Service ready")
        
    except Exception as e:
        logger.error("Startup failed", exc_info=True)
        raise


# Health endpoint
@app.get("/health")
async def health():
    """Comprehensive health check including dependencies."""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check database
    try:
        from app.db.db_client import get_db
        db = await get_db()
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["checks"]["redis"] = "connected"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Celery
    try:
        from app.main import celery
        inspect = celery.control.inspect()
        stats = inspect.stats()
        if stats:
            health_status["checks"]["celery"] = "active"
        else:
            health_status["checks"]["celery"] = "inactive"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["celery"] = f"error: {str(e)}"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


# Readiness probe (for Kubernetes)
@app.get("/ready")
async def readiness():
    """Kubernetes readiness probe."""
    return {"status": "ready"}


# Liveness probe
@app.get("/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Face Recognition API",
        "version": app.version,
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.USE_GPU,  # Disable reload in production/GPU mode
        log_level="info",
        access_log=True
    )
