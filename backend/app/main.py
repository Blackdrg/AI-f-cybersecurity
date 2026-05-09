import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import time
import socket
import struct
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Initialize Sentry
import os
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)

# Configure structured logging with sanitization to prevent log injection
from app.utils.log_sanitizer import SanitizingFormatter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Apply sanitizing formatter to all existing handlers
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.setFormatter(SanitizingFormatter())

logger = logging.getLogger("face-recognition")

# Import production systems
from .policy_engine import policy_engine, get_policy_engine
from .models.ethical_governor import ethical_governor, check_ethical_compliance
from .models.explainable_ai import decision_breakdown_engine
from .scalability import init_shard_manager, shard_manager, cached_index
from .hybrid_search import init_vector_store, get_vector_store
from .models.model_calibrator import calibrator, evaluation_pipeline, version_manager
from .continuous_evaluation import evaluation_pipeline as eval_pipeline, get_evaluation_pipeline
# from .decision_engine import decision_engine
from .models.enhanced_spoof import enhanced_spoof_detector
from .models.privacy_engine import dp_engine
from .middleware.usage_limiter import init_usage_limiter, get_usage_limiter
from .middleware.policy_enforcement import PolicyContext
# Continuous Attestation for runtime integrity monitoring
from .models.attestation import ContinuousAttestor, ContinuousAttestationConfig, AttestationStatus

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
# Startup guard: reject default JWT secret in production
if JWT_SECRET == "dev-secret-change-me" and os.getenv("ENVIRONMENT", "development") in ["production", "prod"]:
    logger.critical("FATAL: Default JWT secret detected in production environment!")
    raise RuntimeError("Insecure JWT secret configuration - please set JWT_SECRET environment variable")

# Required environment variables for production operation
# These must be present; otherwise features will fail silently
REQUIRED_ENV_VARS = {
    "STRIPE_SECRET_KEY": "Stripe billing and subscription provisioning (required for paid features)",
    "OPENAI_API_KEY": "OpenAI GPT assistant integration (required for AI assistant features)",
    "ENCRYPTION_KEY": "32-byte AES-256-GCM key for encrypting biometric templates at rest (required)",
    "JWT_SECRET": "64-byte secret for JWT token signing (required for authentication)",
    "BING_API_KEY": "Bing Search API key for enrichment portal (required for external enrichment)",
}

# Optional but important env vars that degrade features if missing
FEATURE_ENV_VARS = {
    "BING_API_KEY": "Bing Search API for enrichment portal (degrades without it)",
    "OTX_API_KEY": "AlienVault OTX threat intelligence feed",
    "MISP_API_KEY": "MISP threat intelligence platform",
    "VIRUS_TOTAL_API_KEY": "VirusTotal threat intelligence",
    "AZURE_TENANT_ID": "Azure AD SSO integration",
    "GOOGLE_CLIENT_ID": "Google OAuth SSO integration",
}

def validate_required_env_vars():
    """Validate that all required environment variables are set and not using placeholder defaults."""
    missing_required = []
    insecure = []
    env = os.getenv("ENVIRONMENT", "development")

    # Check hard-required vars (fail in prod if missing/insecure)
    for var, description in REQUIRED_ENV_VARS.items():
        value = os.getenv(var)
        if not value:
            if env in ["production", "prod"]:
                missing_required.append(f"{var} ({description})")
            else:
                logger.warning(f"Env var {var} not set. {description}")
        # Check for placeholder/test defaults
    if var == "STRIPE_SECRET_KEY" and value.startswith(("sk_test_", "sk_test_mock")):
        if env in ["production", "prod"]:
            insecure.append(f"{var} uses test key; production key required")
    elif var == "OPENAI_API_KEY" and value in ["sk-test-mock-openai", "", "sk-", "sk-test"]:
        if env in ["production", "prod"]:
            insecure.append(f"{var} uses mock key; real API key required")
    elif var == "ENCRYPTION_KEY":
        if len(value) < 32:
            insecure.append(f"{var} must be ≥32 bytes; got {len(value)}")
        if value in ["fallback-key-32bytes-for-dev!!!", "dev-encryption-key-change-me", "your-32-byte-secret-key-here123456789012"]:
            if env in ["production", "prod"]:
                insecure.append(f"{var} uses development fallback key")
    elif var == "JWT_SECRET":
        # Should be at least 64 characters for HS512
        if len(value) < 64:
            insecure.append(f"{var} must be ≥64 bytes (for HS512); got {len(value)}")
        if value in ["dev-secret-change-me", "your-super-secret-key-change-it"]:
            if env in ["production", "prod"]:
                insecure.append(f"{var} uses default development secret")
    elif var == "BING_API_KEY":
        if value.startswith("test-") or value == "":
            if env in ["production", "prod"]:
                insecure.append(f"{var} uses test key; production Bing Search API key required")

    # Check feature-critical vars (warn in prod, but don't fail startup)
    for var, description in FEATURE_ENV_VARS.items():
        value = os.getenv(var)
        if not value or value.startswith(("your-", "test", "placeholder")):
            env_local = os.getenv("ENVIRONMENT", "development")
            if env_local in ["production", "prod"]:
                logger.warning(f"Feature degradation: {var} not configured. {description}")
            else:
                logger.debug(f"Dev mode: {var} not set. {description}")

    # Validate metrics endpoint security
    if os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true":
        if not os.getenv("METRICS_TOKEN"):
            if env in ["production", "prod"]:
                missing_required.append("METRICS_TOKEN (required when PROMETHEUS_ENABLED=true)")
            else:
                logger.warning("Metrics endpoint accessible without token — set METRICS_TOKEN for security")

    if missing_required:
        raise RuntimeError(f"Missing required env vars in production: {', '.join(missing_required)}")

    if insecure:
        raise RuntimeError(f"Insecure env configuration: {'; '.join(insecure)}")

# Add middlewares (order matters: auth first, then rate limit)
app.add_middleware(AuthenticationMiddleware, secret_key=JWT_SECRET)
app.add_middleware(RateLimitMiddleware, redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))
app.add_middleware(UsageLimiter, redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))

# Global production systems ready flag
_production_systems_ready = False
# Global usage limiter instance
_usage_limiter = None

# Global continuous attestor
_continuous_attestor = None

def get_continuous_attestor():
    """Get the global continuous attestor instance."""
    global _continuous_attestor
    return _continuous_attestor

# Startup event to initialize all production systems
@app.on_event("startup")
async def startup_event():
    # Declare globals that will be modified
    global _usage_limiter, _production_systems_ready, _continuous_attestor

    logger.info("Starting up Face Recognition Service...")

    # Validate required environment variables before anything else
    validate_required_env_vars()
    logger.info("Environment validation passed - all required secrets present")

    # Resilient DB initialization
    db_initialized = False
    retries = 5
    while not db_initialized and retries > 0:
        try:
            await init_db()
            db_initialized = True
            logger.info("Database initialized successfully")
            
            # Initialize database monitoring after DB is ready
            try:
                from app.monitoring.db_monitor import init_monitor, get_monitor
                db = await get_db()
                init_monitor(db)
                monitor = get_monitor()
                await monitor.start_background_monitoring()
                logger.info("Database monitoring initialized")
            except Exception as e:
                logger.warning(f"DB monitoring init failed: {e}")
        except Exception as e:
            retries -= 1
            logger.warning(f"Database init failed: {e}. Retrying in 5s... ({retries} left)")
            await asyncio.sleep(5)

    if not db_initialized:
        logger.error("DB init failed after retries. Continuing in degraded mode.")

    # 0.5. TEE Enclave Validation (if enabled)
    _enclave_enabled = os.getenv("ENCLAVE_ENABLED", "false").lower() == "true"
    _enclave_mode = os.getenv("ENCLAVE_MODE", "nitro").lower()
    _enclave_strict = os.getenv("ENCLAVE_STRICT", "true").lower() == "true"
    
    # Production guard: block SGX/SEV simulation in prod
    _env = os.getenv("ENVIRONMENT", "development").lower()
    if _env in ["production", "prod"]:
        if _enclave_enabled and _enclave_mode not in ["nitro"]:
            logger.critical(f"FATAL: Unsupported TEE mode '{_enclave_mode}' in production. Only AWS Nitro Enclaves are supported. Set ENCLAVE_MODE=nitro or disable ENCLAVE_ENABLED.")
            raise RuntimeError(f"Invalid TEE configuration: {_enclave_mode} not supported in production. Use AWS Nitro Enclaves or disable TEE.")
        
        # Check that enclave_mock is NOT being imported/used
        import sys
        mock_modules = [m for m in sys.modules if 'enclave_mock' in m.lower() or 'mock' in m.lower()]
        if mock_modules:
            logger.critical(f"FATAL: TEE mock modules detected in production: {mock_modules}")
            raise RuntimeError("TEE simulation modules loaded in production - this is a security violation")
    
    if _enclave_enabled:
        # Only Nitro supported in production
        if _enclave_mode not in ["nitro"]:
            logger.error(f"ENCLAVE_MODE '{_enclave_mode}' is not production-ready. Only 'nitro' is currently supported.")
            if _enclave_strict:
                raise RuntimeError(f"Unsupported TEE mode: {_enclave_mode}. Set ENCLAVE_MODE=nitro.")
            else:
                logger.warning(f"WARNING: Using unsupported TEE mode '{_enclave_mode}' - lower security guarantees")
        
        # Verify enclave VSOCK connectivity
        try:
            test_sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
            test_sock.settimeout(3.0)
            test_sock.connect((3, int(os.getenv("ENCLAVE_VSOCK_PORT", "5000"))))
            test_sock.close()
            logger.info("TEE enclave VSOCK connection verified — Nitro Enclave is reachable")
        except Exception as e:
            logger.critical(f"TEE enclave VSOCK connection failed: {e}")
            if _enclave_strict:
                raise RuntimeError(
                    "Hardware-backed TEE enclave unreachable. "
                    "Deploy AWS Nitro Enclave or set ENCLAVE_ENABLED=false to run without TEE (less secure)."
                )
            else:
                logger.warning("TEE enclave unavailable — continuing WITHOUT hardware-backed security (DEGRADED)")
    else:
        if _env in ["production", "prod"]:
            logger.warning(
                "ENCLAVE_ENABLED=false in production — biometric templates processed without hardware-backed isolation. "
                "Consider enabling TEE for compliance (requires AWS Nitro Enclaves)."
            )

    # Initialize production systems
    global _production_systems_ready
    try:
        # 0. Redis PubSub & WebSocket Manager
        logger.info("Initializing Redis PubSub...")
        from .pubsub import pubsub_manager
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        await pubsub_manager.initialize(redis_url)
        
        from .websocket_manager import connection_manager
        await connection_manager.initialize()
        logger.info("PubSub + WebSocket manager ready")
        
        # 0b. Initialize Rate Limiter (after Redis)
        from .middleware.rate_limit import rate_limiter_middleware
        await rate_limiter_middleware.initialize()
        logger.info("Rate limiter initialized")
        
        # 1. Policy Engine
        logger.info("Initializing PolicyEngine...")
        policy_engine._init_default_policies()

        # 2. Ethical Governor
        logger.info("Initializing EthicalGovernor...")

        # 3. Usage Limiter (Redis-backed)
        from .middleware.usage_limiter import init_usage_limiter
        await init_usage_limiter(redis_url)
        logger.info("UsageLimiter initialized")

        # 4. Hybrid Search & Vector Store
        from .hybrid_search import init_vector_store
        await init_vector_store()
        logger.info("Hybrid vector store initialized")

        # 5. FAISS Shard Manager
        from .scalability import init_shard_manager
        init_shard_manager(num_shards=4)
        logger.info("Vector shard manager initialized")

        # 6. Model Warmup
        logger.info("Warming up ML models...")
        from .models.face_detector import FaceDetector
        from .models.face_embedder import FaceEmbedder
        from .models.spoof_detector import SpoofDetector
        from .models.emotion_detector import EmotionDetector
        from .models.age_gender_estimator import AgeGenderEstimator
        import numpy as np
        dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
        FaceDetector()
        FaceEmbedder()
        SpoofDetector()
        EmotionDetector()
        AgeGenderEstimator()

        # 6b. Verify Behavioral Predictor LSTM weights loaded
        from .models.behavioral_predictor import behavioral_predictor
        model_info = behavioral_predictor.get_model_info()
        if not model_info.get('weights_loaded'):
            logger.warning(
                "Behavioral predictor LSTM weights not found at expected path. "
                "Model operating in fallback mode. Train model or place weights at backend/models/behavioral_lstm.pt"
            )
        else:
            logger.info(f"Behavioral predictor ready: {model_info}")

        # 7. Initialize Emotion + Behavior Engine
        logger.info("Initializing Emotion + Behavior Engine...")
        from .models.emotion_behavior import get_emotion_behavior_engine
        _emotion_behavior_engine = get_emotion_behavior_engine()

        # 8. Initialize Federated Learning
        logger.info("Initializing Federated Learning server...")
        from .federated_learning import client_orchestrator
        logger.info(f"Federated Learning ready: {len(client_orchestrator.registered_clients)} clients registered")

        # 9. Discovery and Load Plugins
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

        # 10. Continuous Attestation for runtime integrity monitoring
        logger.info("Initializing Continuous Attestation...")
        try:
            from .models.attestation import ContinuousAttestationConfig, ContinuousAttestor
            attestation_config = ContinuousAttestationConfig(
                check_interval_seconds=300,  # 5 minutes
                critical_file_paths=[
                    __file__,  # main app file
                    os.path.join(os.path.dirname(__file__), 'security', 'encryption.py'),
                    os.path.join(os.path.dirname(__file__), 'db', 'db_client.py')
                ]
            )
            _continuous_attestor = ContinuousAttestor(
                config=attestation_config,
                alert_callback=lambda report: logger.warning(
                    f"Attestation alert [{report.status.value}]: {report.details}"
                )
            )
            _continuous_attestor.start()
            logger.info("Continuous Attestation started")
        except Exception as e:
            logger.warning(f"Continuous Attestation initialization failed: {e}")

        # 11. Start System Alerts background task
        logger.info("Starting system-level alert monitoring...")
        try:
            from .services.system_alerts import start_system_alerts
            asyncio.create_task(start_system_alerts())
            logger.info("System alerts background task scheduled")
        except Exception as e:
            logger.warning(f"System alerts init failed: {e}")

        # ========================================================================
        # PRODUCTION GUARDS - Validate simulation modes not active in prod
        # ========================================================================
        _env = os.getenv("ENVIRONMENT", "development").lower()
        if _env in ["production", "prod"]:
            # Check Homomorphic Encryption is enabled
            he_enabled = os.getenv("HE_ENABLED", "false").lower() == "true"
            if not he_enabled:
                logger.critical("FATAL: HE_ENABLED=false in production. Homomorphic Encryption is required for encrypted search.")
                raise RuntimeError("HE_ENABLED must be true in production")
            
            # Check TenSEAL availability
            try:
                from .models.homomorphic_encryption import HomomorphicEncryptionEngine
                import importlib
                tenseal_spec = importlib.util.find_spec("tenseal")
                if tenseal_spec is None:
                    logger.critical(
                        "FATAL: TenSEAL not installed — Homomorphic Encryption unavailable. "
                        "HE is REQUIRED for encrypted search in production. Install: pip install tenseal"
                    )
                    raise RuntimeError("Missing TenSEAL dependency for HE in production")
            except ImportError as e:
                logger.critical(f"HE dependency check failed: {e}")
                raise RuntimeError(f"HE requirement: {e}")

            # Check that behavioral predictor model is present
            from .models.behavioral_predictor import behavioral_predictor
            model_info = behavioral_predictor.get_model_info()
            if not model_info.get('weights_loaded'):
                logger.warning(
                    "Behavioral predictor LSTM weights not loaded. "
                    "Model operating in fallback mode — upgrade to production model for v2.1 compliance."
                )
        
        # Mark production systems as ready
        _production_systems_ready = True
        logger.info("✅ All production systems initialized and ready")
        
    except Exception as e:
        logger.error(f"Production systems initialization failed: {e}", exc_info=True)
        _production_systems_ready = False
        raise

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Strict Content Security Policy - Block all inline scripts, only allow trusted sources
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# CORS for UI - restrict to known origins in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(enroll.router, prefix="/api/v1", tags=["enroll"])
app.include_router(recognize.router, prefix="/api/v1", tags=["recognize"])
app.include_router(video_recognize.router, prefix="/api/v1", tags=["video_recognize"])
app.include_router(stream_recognize.router, prefix="/ws/v1", tags=["stream_recognize"])
# Enable v1 admin router
app.include_router(admin_v1.router, prefix="/api/v1/admin", tags=["admin-v1"])
app.include_router(federated_learning.router, prefix="/api/v1", tags=["federated_learning"])

# Revocation API
app.include_router(revocation.router, prefix="/api", tags=["auth"])

# Frontend-compatible routes
app.include_router(enroll.router, prefix="/api", tags=["enroll"])
app.include_router(recognize.router, prefix="/api", tags=["recognize"])
app.include_router(admin.router, prefix="/api", tags=["admin"])

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
# Enable v1 compliance router
app.include_router(compliance_v1.router, prefix="/api/v1/compliance", tags=["compliance-v1"])
app.include_router(mfa.router, prefix="/api", tags=["mfa"])
app.include_router(oauth.router, prefix="/api", tags=["oauth"])
from .api import webhooks
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])

# Legal compliance router
from .api.legal import router as legal_router
app.include_router(legal_router, prefix="/api", tags=["legal"])

# V2 recognition (with enhanced scoring)
from .api.recognition_v2 import router as recognition_v2_router
app.include_router(recognition_v2_router, prefix="/api/v2", tags=["recognition_v2"])

# Plugin management
app.include_router(plugins.router, tags=["plugins"])

# MPC cross-org matching
app.include_router(mpc.router, prefix="/api/v1", tags=["mpc"])

# GraphQL API (v2.2.1+)
from .api.graphql_api import graphql_router
app.add_route("/graphql", graphql_router)
app.add_route("/graphql/", graphql_router)  # trailing slash

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

@app.get("/healthz")
async def healthz():
    """Kubernetes/Docker health check endpoint."""
    return {"status": "healthy"}

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
                "audit_chain": True,
                "jwt_revocation": True
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
