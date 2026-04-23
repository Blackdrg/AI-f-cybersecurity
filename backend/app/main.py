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
from .api import orgs, cameras, events, alerts, analytics, logs, access
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

# Import core models...
# [All previous imports and globals...]

app = FastAPI(title="Face Recognition Service", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routers
app.include_router(enroll.router, prefix="/api", tags=["enroll"])
app.include_router(recognize.router, prefix="/api", tags=["recognize"])
app.include_router(video_recognize.router, prefix="/api", tags=["video_recognize"])
app.include_router(stream_recognize.router, prefix="/ws", tags=["stream_recognize"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(federated_learning.router, prefix="/api", tags=["federated_learning"])

# Optional feature routers (lazy load to avoid import errors)
try:
    from .api import users
    app.include_router(users.router, prefix="/api", tags=["users"])
except ImportError as e:
    logger.warning(f"Users module not available: {e}")
try:
    from .api import plans
    app.include_router(plans.router, prefix="/api", tags=["plans"])
except ImportError as e:
    logger.warning(f"Plans module not available: {e}")
try:
    from .api import subscriptions
    app.include_router(subscriptions.router, prefix="/api", tags=["subscriptions"])
except ImportError as e:
    logger.warning(f"Subscriptions module not available: {e}")
try:
    from .api import payments
    app.include_router(payments.router, prefix="/api", tags=["payments"])
except ImportError as e:
    logger.warning(f"Payments module not available: {e}")
try:
    from .api import usage
    app.include_router(usage.router, prefix="/api", tags=["usage"])
except ImportError as e:
    logger.warning(f"Usage module not available: {e}")
try:
    from .api import ai_assistant
    app.include_router(ai_assistant.router, prefix="/api", tags=["ai_assistant"])
except ImportError as e:
    logger.warning(f"AI Assistant module not available: {e}")
try:
    from .api import support
    app.include_router(support.router, prefix="/api", tags=["support"])
except ImportError as e:
    logger.warning(f"Support module not available: {e}")
try:
    from .api import public_enrich
    app.include_router(public_enrich.router, prefix="/api", tags=["public_enrich"])
except ImportError as e:
    logger.warning(f"Public enrich module not available: {e}")
app.include_router(orgs.router, prefix="/api", tags=["orgs"])
app.include_router(cameras.router, prefix="/api/orgs", tags=["cameras"])
app.include_router(events.router, prefix="/api/orgs", tags=["events"])
app.include_router(alerts.router, prefix="/api/orgs", tags=["alerts"])
app.include_router(analytics.router, prefix="/api/orgs", tags=["analytics"])
app.include_router(logs.router, prefix="/api/orgs", tags=["logs"])
app.include_router(access.router, prefix="/api/orgs", tags=["access"])

from .api.legal import router as legal_router
app.include_router(legal_router, prefix="/api", tags=["legal"])

from .api.recognition_v2 import router as recognition_v2_router
app.include_router(recognition_v2_router, prefix="/api", tags=["recognition_v2"])

# Setup
setup_security(app)
setup_metrics(app)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Face Recognition Service...")
    await init_db()  # Resilient retries already in func
    # Model warmup...
    logger.info("Ready")

@app.get("/health")
async def health():
    return {"status": "ok"}

# Other endpoints...

if __name__ == "__main__":
    async def run_servers():
        grpc_task = asyncio.create_task(serve_grpc())
        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()
    asyncio.run(run_servers())

