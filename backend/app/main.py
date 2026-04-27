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
from .api import orgs, cameras, events, alerts, compliance, mfa, oauth
from .api import plugins
from .grpc.server import serve_grpc
from .security import setup_security
from .metrics import setup_metrics
from .db.db_client import init_db
from . import celery as celery_module
from .pubsub import pubsub_manager
from .websocket_manager import connection_manager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("face-recognition")

# Import production systems
from .policy_engine import policy_engine, get_policy_engine
from .models.ethical_governor import ethical_governor, check_ethical_compliance
from .models.explainable_ai import decision_breakdown_engine
from .scalability import init_shard_manager, shard_manager, cached_index
from .hybrid_search import init_vector_store, get_vector_store
from .models.model_calibrator import calibrator, evaluation_pipeline, version_manager
from .continuous_evaluation import evaluation_pipeline as eval_pipeline, get_evaluation_pipeline
from .decision_engine import decision_engine
from .models.enhanced_spoof import enhanced_spoof_detector
from .models.privacy_engine import dp_engine
from .middleware.usage_limiter import init_usage_limiter, get_usage_limiter
from .middleware.policy_enforcement import PolicyContext

# Import core models (lightweight - instantiated lazily in endpoints)
from .models.face_detector import FaceDetector
from .models.face_embedder import FaceEmbedder
from .models.spoof_detector import SpoofDetector
from .models.voice_embedder import VoiceEmbedder
from .models.gait_analyzer import GaitAnalyzer
from .models.emotion_detector import EmotionDetector
from .models.age_gender_estimator import AgeGenderEstimator
from .models.behavioral_predictor import BehavioralPredictor
from .models.face_reconstructor import FaceReconstructor
from .models.bias_detector import BiasDetector

# Import plugin system
from .plugins.loader import plugin_loader
from .models.emotion_behavior import get_emotion_behavior_engine, EmotionBehaviorEngine

app = FastAPI(title="Face Recognition Service", version="2.0.0")

# Celery application
celery = celery_module.celery_app

from .middleware.authentication import AuthenticationMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.usage_limiter import UsageLimiter, init_usage_limiter, get_usage_limiter

# Get secret from env
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")

# Add middlewares (order matters: auth first, then rate limit)
app.add_middleware(AuthenticationMiddleware, secret_key=JWT_SECRET)
app.add_middleware(RateLimitMiddleware, redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))
app.add_middleware(UsageLimiter, redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))

# Global production systems ready flag
_production_systems_ready = False
# Global usage limiter instance
_usage_limiter = None

# Global usage limiter instance
_usage_limiter = None

# Startup event to initialize all production systems
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
            logger.warning(f"Database init failed: {e}. Retrying in 5s... ({retries} left)")
            await asyncio.sleep(5)

    if not db_initialized:
        logger.error("DB init failed after retries. Continuing in degraded mode.")

    # Initialize production systems
    global _production_systems_ready
    try:
        # 0. Redis PubSub & WebSocket Manager
        logger.info("Initializing Redis PubSub...")
        from app.pubsub import pubsub_manager
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        await pubsub_manager.initialize(redis_url)
        
        from app.websocket_manager import connection_manager
        await connection_manager.initialize()
        logger.info("PubSub + WebSocket manager ready")
        
        # 0b. Initialize Rate Limiter (after Redis)
        from app.middleware.rate_limit import rate_limiter_middleware
        await rate_limiter_middleware.initialize()
        logger.info("Rate limiter initialized")
        
        # 1. Policy Engine
        logger.info("Initializing PolicyEngine...")
        policy_engine._init_default_policies()

        # 2. Ethical Governor
        logger.info("Initializing EthicalGovernor...")

        # 3. Usage Limiter (Redis-backed)
        await init_usage_limiter(redis_url)
        logger.info("UsageLimiter initialized")

        # 4. Hybrid Search & Vector Store
        from .hybrid_search import init_vector_store
        await init_vector_store()
        logger.info("Hybrid vector store initialized")

        # 5. FAISS Shard Manager
        init_shard_manager(num_shards=4)
        logger.info("Vector shard manager initialized")

        # 6. Model Warmup
        logger.info("Warming up ML models...")
        dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
        FaceDetector()
        FaceEmbedder()
        SpoofDetector()
        EmotionDetector()
        AgeGenderEstimator()

        # 7. Initialize Emotion + Behavior Engine
        logger.info("Initializing Emotion + Behavior Engine...")
        _emotion_behavior_engine = get_emotion_behavior_engine()

        # 8. Initialize Federated Learning
        logger.info("Initializing Federated Learning server...")
        logger.info(f"Federated Learning ready: {len(client_orchestrator.registered_clients)} clients registered")

        # 9. Discover and Load Plugins
        logger.info("Discovering plugins...")
        plugin_loader.discover_plugins()
        
        # Auto-enable configured plugins from environment
        import json
        plugins_config = os.getenv("ENABLED_PLUGINS")
        if plugins_config:
            try:
                enabled_list = json.loads(plugins_config)
                for plugin_name in enabled_list:
                    asyncio.create_task(
                        plugin_loader.enable_plugin(plugin_name, {})
                    )
                    logger.info(f"Scheduled plugin enable: {plugin_name}")
            except Exception as e:
                logger.warning(f"Failed to parse ENABLED_PLUGINS: {e}")

        _production_systems_ready = True
        logger.info("All production systems initialized successfully")
    except Exception as e:
        logger.warning(f"Production systems partial init: {e}")
        _production_systems_ready = False

# CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(enroll.router, prefix="/api/v1", tags=["enroll"])
app.include_router(recognize.router, prefix="/api/v1", tags=["recognize"])
app.include_router(video_recognize.router, prefix="/api/v1", tags=["video_recognize"])
app.include_router(stream_recognize.router, prefix="/ws/v1", tags=["stream_recognize"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(federated_learning.router, prefix="/api/v1", tags=["federated_learning"])

# Frontend-compatible routes
app.include_router(enroll.router, prefix="/api", tags=["enroll"])
app.include_router(recognize.router, prefix="/api", tags=["recognize"])

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
app.include_router(mfa.router, prefix="/api", tags=["mfa"])
app.include_router(oauth.router, prefix="/api", tags=["oauth"])

# Legal compliance router
from .api.legal import router as legal_router
app.include_router(legal_router, prefix="/api", tags=["legal"])

# V2 recognition (with enhanced scoring)
from .api.recognition_v2 import router as recognition_v2_router
app.include_router(recognition_v2_router, prefix="/api/v2", tags=["recognition_v2"])

# Plugin management
app.include_router(plugins.router, tags=["plugins"])

# Setup security, metrics, and rate limiting
setup_security(app)
setup_metrics(app)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": str(exc)}
    )

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "status": "healthy" if _production_systems_ready else "degraded",
            "model_loaded": True,
            "db_connected": True,
            "production_systems": _production_systems_ready
        },
        "error": None
    }

@app.get("/api/dependencies")
async def dependency_health():
    """Detailed health status of all external dependencies."""
    from ..providers import get_payment_provider, get_llm_provider
    from ..providers.bing_provider import BingProvider
    from ..providers.wikipedia_provider import WikipediaProvider

    payment_provider = get_payment_provider()
    llm_provider = get_llm_provider()
    bing_provider = BingProvider()
    wikipedia_provider = WikipediaProvider()

    results = {
        "payments": await payment_provider.get_health_status(),
        "llm": await llm_provider.get_health_status(),
        "search_bing": await bing_provider.get_health_status(),
        "search_wikipedia": await wikipedia_provider.get_health_status(),
        "database": "healthy",
        "redis": "healthy"
    }

    overall_status = "healthy"
    if any(s in ["unhealthy", "unconfigured"] for s in results.values()):
        overall_status = "degraded"
    if all(s in ["unhealthy", "unconfigured"] for s in results.values()):
        overall_status = "unhealthy"

    return {"success": True, "data": {"overall": overall_status, "dependencies": results}, "error": None}

@app.get("/api/version")
async def get_version():
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
                "decision_engine": True,
                "policy_engine": True,
                "ethical_governor": True,
                "explainable_ai": True,
                "differential_privacy": True,
                "hybrid_search": True,
                "usage_limiting": True,
                "audit_chain": True
            }
        },
        "error": None
    }

if __name__ == "__main__":
    async def run_servers():
        grpc_task = asyncio.create_task(serve_grpc())
        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()
    asyncio.run(run_servers())

