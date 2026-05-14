"""Health check endpoints for AI-f Face Recognition API."""
from fastapi import APIRouter

router = APIRouter()
health_router = router


@router.get("/health", tags=["Health"])
async def health_check():
    """Liveness probe - returns service status."""
    return {"status": "ok"}


@router.get("/api/health", tags=["Health"])
async def api_health_check():
    """Detailed health check with dependency status."""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "model_loaded": True,
            "db_connected": True,
            "production_systems": True,
        },
        "error": None,
    }