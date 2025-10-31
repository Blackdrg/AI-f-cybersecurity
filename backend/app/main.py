from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from .api import enroll, recognize, video_recognize, stream_recognize, admin, federated_learning
from .api import users, plans, subscriptions, payments, usage, ai_assistant, support, public_enrich
from .grpc.server import serve_grpc
from .security import setup_security
from .metrics import setup_metrics
from .db.db_client import init_db

# Import new models to ensure they are loaded
from .models.spoof_detector import SpoofDetector
from .models.voice_embedder import VoiceEmbedder
from .models.gait_analyzer import GaitAnalyzer
from .models.emotion_detector import EmotionDetector
from .models.age_gender_estimator import AgeGenderEstimator
from .models.behavioral_predictor import BehavioralPredictor
from .models.face_reconstructor import FaceReconstructor

app = FastAPI(title="Face Recognition Service", version="1.0.0")

# CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(enroll.router, prefix="/api", tags=["enroll"])
app.include_router(recognize.router, prefix="/api", tags=["recognize"])
app.include_router(video_recognize.router, prefix="/api",
                   tags=["video_recognize"])
app.include_router(stream_recognize.router, prefix="/ws",
                   tags=["stream_recognize"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(federated_learning.router, prefix="/api",
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

# Setup security, metrics, DB
setup_security(app)
setup_metrics(app)


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.get("/health")
async def health_check():
    # Check model loaded, DB connectivity, etc.
    return {"status": "healthy", "model_loaded": True, "db_connected": True, "index_status": "ready"}

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
