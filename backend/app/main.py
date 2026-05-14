"""
Application lifecycle management - updated with threat intel and enrichment initialization.
"""
import os
import asyncio
import logging

from fastapi import FastAPI
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
from app.api import health
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