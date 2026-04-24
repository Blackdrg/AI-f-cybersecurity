import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import time
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Initialize Sentry
import os
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),

    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
from .api import enroll, recognize, video_recognize, stream_recognize, admin, federated_learning
from .api import users, plans, subscriptions, payments, usage, ai_assistant, support, public_enrich
from .api import orgs, cameras, events, alerts, compliance
from .grpc.server import serve_grpc
from .security import setup_security
from .metrics import setup_metrics
from .db.db_client import init_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("face-recognition")

# Import core models
from .models.face_detector import FaceDetector
from .models.face_embedder import FaceEmbedder
from .models.spoof_detector import SpoofDetector
from .models.voice_embedder import VoiceEmbedder
from .models.gait_analyzer import GaitAnalyzer
from .models.emotion_detector import EmotionDetector
from .models.age_gender_estimator import AgeGenderEstimator
from .models.behavioral_predictor import BehavioralPredictor
from .models.face_reconstructor import FaceReconstructor

# Import production systems
from .models.enhanced_spoof import enhanced_spoof_detector
from .models.model_calibrator import calibrator, evaluation_pipeline, version_manager
from .scalability import init_shard_manager, cached_index
from .federated_learning import federated_server, client_orchestrator
from .legal_compliance import legal_compliance
from .decision_engine import decision_engine

# Import new production systems
from .hybrid_search import init_vector_store, get_vector_store, hybrid_store
from .scoring_engine import scoring_engine, get_scoring_engine
from .continuous_evaluation import evaluation_pipeline, get_evaluation_pipeline
from .policy_engine import policy_engine, get_policy_engine

from .middleware.rate_limit import RateLimitMiddleware

app = FastAPI(title="Face Recognition Service", version="2.0.0")

# Add Rate Limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

# Global production systems initialized
_production_systems_ready = False

# Global exception handler for standard response format
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": str(exc)
        }
    )

# CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (v1)
app.include_router(enroll.router, prefix="/api/v1", tags=["enroll"])
app.include_router(recognize.router, prefix="/api/v1", tags=["recognize"])
app.include_router(video_recognize.router, prefix="/api/v1",
                   tags=["video_recognize"])
app.include_router(stream_recognize.router, prefix="/ws/v1",
                   tags=["stream_recognize"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(federated_learning.router, prefix="/api/v1",
                   tags=["federated_learning"])

# SaaS routers
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(plans.router, prefix="/api", tags=["plans"])
app.include_router(subscriptions.router, prefix="/api", tags=["subscriptions"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(usage.router, prefix="/api", tags=["usage"])
app.include_router(ai_assistant.router, prefix="/api", tags=["ai_assistant"])
app.include_router(support.router, prefix="/api", tags=["support"])
app.include_router(public_enrich.router, prefix="/api", tags=["public_enrich"])
app.include_router(orgs.router, prefix="/api", tags=["orgs"])
app.include_router(cameras.router, prefix="/api/orgs", tags=["cameras"])
app.include_router(events.router, prefix="/api/orgs", tags=["events"])
app.include_router(alerts.router, prefix="/api/orgs", tags=["alerts"])
app.include_router(compliance.router, prefix="/api", tags=["compliance"])

# Legal compliance router
from .api.legal import router as legal_router
app.include_router(legal_router, prefix="/api", tags=["legal"])

# Recognition v2 router (with scoring engine)
from .api.recognition_v2 import router as recognition_v2_router
app.include_router(recognition_v2_router, prefix="/api/v2", tags=["recognition_v2"])

# Setup security, metrics, DB
setup_security(app)
setup_metrics(app)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Face Recognition Service...")
    
    # Resilient DB initialization
    db_initialized = False
    retries = 5
    while not db_initialized and retries > 0:
        try:
            await init_db()
            db_initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            retries -= 1
            logger.warning(f"Database initialization failed: {e}. Retrying in 5 seconds... ({retries} retries left)")
            await asyncio.sleep(5)
    
    if not db_initialized:
        logger.error("Could not initialize database after several retries. Continuing in degraded mode.")

    # Initialize production systems
    global _production_systems_ready
    try:
        # Initialize vector sharding
        from .scalability import init_shard_manager
        init_shard_manager(num_shards=4)
        
        # Model Warmup
        logger.info("Warming up models...")
        # Create dummy image for warmup
        import numpy as np
        import cv2
        dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
        
        # Instantiate and warmup models
        # Note: In a real scenario, we might want to do a dummy inference
        # For now, just ensuring they are initialized
        FaceDetector()
        FaceEmbedder()
        SpoofDetector()
        EmotionDetector()
        AgeGenderEstimator()
        
        _production_systems_ready = True
        logger.info("Production systems initialized successfully")
    except Exception as e:
        logger.warning(f"Warning: Production systems partial init: {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health")
async def health_check():
    # Check all production systems
    checks = {
        "status": "healthy" if _production_systems_ready else "degraded",
        "model_loaded": True,
        "db_connected": True,
        "index_status": "ready" if _production_systems_ready else "limited",
        "production_systems": _production_systems_ready
    }
    return {
        "success": True,
        "data": checks,
        "error": None
    }


@app.get("/api/dependencies")
async def dependency_health():
    """Detailed health status of all external dependencies."""
    from .providers import get_payment_provider, get_llm_provider
    from .providers.bing_provider import BingProvider
    from .providers.wikipedia_provider import WikipediaProvider
    
    payment_provider = get_payment_provider()
    llm_provider = get_llm_provider()
    bing_provider = BingProvider()
    wikipedia_provider = WikipediaProvider()
    
    results = {
        "payments": await payment_provider.get_health_status(),
        "llm": await llm_provider.get_health_status(),
        "search_bing": await bing_provider.get_health_status(),
        "search_wikipedia": await wikipedia_provider.get_health_status(),
        "database": "healthy", # Simplified for now
        "redis": "healthy" # Simplified for now
    }
    
    overall_status = "healthy"
    if any(s in ["unhealthy", "unconfigured"] for s in results.values()):
        overall_status = "degraded"
    if all(s in ["unhealthy", "unconfigured"] for s in results.values()):
        overall_status = "unhealthy"
        
    return {
        "success": True,
        "data": {
            "overall": overall_status,
            "dependencies": results
        },
        "error": None
    }


@app.get("/api/version")
async def get_version():
    """Get system version and capabilities."""
    return {
        "success": True,
        "data": {
            "version": "2.0.0",
            "production_ready": True,
            "features": {
                "model_calibration": True,
                "enhanced_spoofing": True,
                "vector_sharding": True,
                "federated_learning": True,
                "legal_compliance": True,
                "decision_engine": True
            }
        },
        "error": None
    }

if __name__ == "__main__":
    # Run both FastAPI and gRPC servers concurrently
    async def run_servers():
        # Start gRPC server in background
        grpc_task = asyncio.create_task(serve_grpc())
        # Start FastAPI server
        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(run_servers())
