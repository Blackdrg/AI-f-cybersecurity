"""
Application lifecycle management - updated with threat intel and enrichment initialization.
"""
import os
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app.monitoring.db_monitor import init_monitor, get_monitor
from app.db.db_client import DBClient, get_db
from app.services.redis_client import RedisClient, get_redis
from app.pubsub import RedisPubSubManager
from app.api.v1 import api_router
from app.api import health, admin
from app.api.enroll import router as enroll_router
from app.api.recognize import router as recognize_router
from app.api.federated_learning import router as federated_learning_router
from app.api.webhooks import router as webhooks_router
from app.api.payments import router as payments_router
from app.api.orgs import router as orgs_router
from app.api.users import router as users_router
from app.api.events import router as events_router
from app.api.usage import router as usage_router
from app.api.subscriptions import router as subscriptions_router
from app.api.support import router as support_router
from app.api.mfa import router as mfa_router
from app.api.oauth import router as oauth_router
from app.api.revocation import router as revocation_router
from app.api.cameras import router as cameras_router
from app.api.video_recognize import router as video_recognize_router
from app.api.stream_recognize import router as stream_recognize_router
from app.api.recognition_v2 import router as recognition_v2_router
from app.api.public_enrich import router as public_enrich_router
from app.api.plans import router as plans_router
from app.api.legal import router as legal_router
from app.api.consent import router as consent_router
from app.api.mpc import router as mpc_router
from app.api.plugins import router as plugins_router
from app.api.ai_assistant import router as ai_assistant_router
from app.api.alerts import router as alerts_router
from app.api.scim import router as scim_router
from app.middleware.security import SecurityHeadersMiddleware, RequestLimitsMiddleware, SanitizationMiddleware
from app.middleware.brute_force import BruteForceMiddleware
from starlette_context import middleware as context_middleware
import time
from app.services.threat_enrichment_pipeline import ThreatEnrichmentPipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management with enhanced service initialization."""
    logger.info("Starting AI-f backend services...")

    # Initialize database
    db_client = DBClient(
        read_replicas=os.getenv('DB_READ_REPLICAS', '').split(',')
    )
    await db_client.init_db()
    app.state.db = db_client

    # Initialize Redis
    redis_client = RedisClient(
        url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
        password=os.getenv('REDIS_PASSWORD')
    )
    await redis_client.connect()
    app.state.redis = redis_client

    # Initialize monitoring
    monitor = init_monitor(db_client)
    await monitor.start_background_monitoring()
    app.state.monitor = monitor

    # Initialize Pub/Sub
    pubsub = RedisPubSubManager.get_instance()
    await pubsub.initialize(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    app.state.pubsub = pubsub

    # Initialize Threat Enrichment Pipeline
    enrichment_pipeline = ThreatEnrichmentPipeline()
    await enrichment_pipeline.initialize()
    app.state.enrichment_pipeline = enrichment_pipeline

    # Initialize threat intel provider
    try:
        from app.providers.enhanced_threat_intel import ThreatIntelProvider
        ti_provider = ThreatIntelProvider()
        await ti_provider.initialize()
        app.state.ti_provider = ti_provider
    except Exception as e:
        logger.warning(f"Threat intel provider initialization failed: {e}")

    # Initialize IOC repository
    try:
        from app.services.ioc_repository import get_ioc_repository
        ioc_repo = get_ioc_repository()
        await ioc_repo.initialize()
        await ioc_repo.create_tables()
    except Exception as e:
        logger.warning(f"IOC repository initialization failed: {e}")

    logger.info("All services initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down AI-f backend services...")
    await monitor.stop_background_monitoring()
    await pubsub.close()
    await redis_client.disconnect()

    if hasattr(app.state, 'enrichment_pipeline'):
        await app.state.enrichment_pipeline.shutdown()

    logger.info("All services shut down cleanly")


# Application instance
app = FastAPI(
    title="AI-f Face Recognition API",
    description="Professional face recognition and identity management platform",
    version="2.5.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLimitsMiddleware, max_request_size=10 * 1024 * 1024)  # 10MB limit
app.add_middleware(BruteForceMiddleware, max_attempts=5)
app.add_middleware(SanitizationMiddleware)

@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30.0)
    except asyncio.TimeoutError:
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=504,
            content={"success": False, "error": "Request timed out"}
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Routes
app.include_router(api_router, prefix='/api/v1')
app.include_router(health.health_router)
app.include_router(admin.router, prefix='/api')
app.include_router(enroll_router, prefix='/api')
app.include_router(recognize_router, prefix='/api')
app.include_router(federated_learning_router, prefix='/api')
app.include_router(webhooks_router, prefix='/api')
app.include_router(payments_router, prefix='/api')
app.include_router(orgs_router, prefix='/api')
app.include_router(users_router, prefix='/api')
app.include_router(events_router, prefix='/api')
app.include_router(usage_router, prefix='/api')
app.include_router(subscriptions_router, prefix='/api')
app.include_router(support_router, prefix='/api')
app.include_router(mfa_router, prefix='/api')
app.include_router(oauth_router, prefix='/api')
app.include_router(revocation_router, prefix='/api')
app.include_router(cameras_router, prefix='/api')
app.include_router(video_recognize_router, prefix='/api')
app.include_router(stream_recognize_router, prefix='/api')
app.include_router(recognition_v2_router, prefix='/api')
app.include_router(public_enrich_router, prefix='/api')
app.include_router(plans_router, prefix='/api')
app.include_router(legal_router, prefix='/api')
app.include_router(consent_router, prefix='/api')
app.include_router(mpc_router, prefix='/api')
app.include_router(plugins_router, prefix='/api')
app.include_router(ai_assistant_router, prefix='/api')
app.include_router(alerts_router, prefix='/api')
app.include_router(scim_router, prefix='/api')


@app.get('/healthz')
async def root_health():
    return {'status': 'ok', 'service': 'ai-f-backend', 'version': '2.5.0'}


@app.get('/metrics')
async def prometheus_metrics():
    from app.monitoring.db_monitor import get_monitor
    monitor = get_monitor()
    return monitor.get_prometheus_metrics()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8000)),
        workers=int(os.getenv('WORKERS', 4)),
        log_level=os.getenv('LOG_LEVEL', 'info'),
    )