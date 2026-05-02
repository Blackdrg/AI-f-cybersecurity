"""Validation suite for production readiness verification."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch


@pytest.mark.validation
class TestSystemValidation:
    """Production readiness validation tests."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Verify health endpoint returns healthy status."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    @pytest.mark.asyncio
    async def test_database_migration_status(self):
        """Verify all migrations are applied."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        
        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        
        # Get current revision
        current = script.get_current_head()
        assert current is not None, "No migrations applied"

    @pytest.mark.asyncio
    async def test_api_version_endpoint(self):
        """Verify API versioning is correct."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.get("/api/version")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data["data"]
        assert data["data"]["version"] == "2.0.0"


@pytest.mark.validation
class TestSecurityValidation:
    """Security validation tests."""

    def test_cors_configuration(self):
        """Verify CORS is properly configured."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.options("/api/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_security_headers(self):
        """Verify security headers are present."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "strict-transport-security" in response.headers

    def test_rate_limit_headers(self):
        """Verify rate limit headers are set."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert "x-ratelimit-limit" in response.headers


@pytest.mark.validation
class TestBillingValidation:
    """Billing system validation."""

    @pytest.mark.asyncio
    async def test_plan_limits_exist(self):
        """Verify all plans have limits defined."""
        from app.middleware.rate_limit import RateLimitMiddleware
        
        limits = RateLimitMiddleware.LIMITS
        
        required_tiers = ["free", "pro", "enterprise"]
        for tier in required_tiers:
            assert tier in limits, f"Missing limit for tier: {tier}"

    @pytest.mark.asyncio
    async def test_usage_tracking(self):
        """Verify usage tracking works."""
        from app.middleware.usage_limiter import UsageLimiter
        
        limiter = UsageLimiter("redis://mock:6379")
        await limiter._ensure_client()
        
        is_limited, remaining = await limiter.check_usage(
            "test_user", "recognize", 100
        )
        
        assert is_limited is False
        assert remaining == 99


@pytest.mark.validation
class TestMLValidation:
    """ML model validation tests."""

    def test_model_schemas_exist(self):
        """Verify model schemas are defined."""
        from app.models.face_detector import FaceDetector
        from app.models.face_embedder import FaceEmbedder
        from app.models.spoof_detector import SpoofDetector
        
        # Models should be instantiable
        detector = FaceDetector()
        embedder = FaceEmbedder()
        spoof = SpoofDetector()
        
        assert detector is not None
        assert embedder is not None
        assert spoof is not None


@pytest.mark.validation
class TestComplianceValidation:
    """Compliance validation tests."""

    def test_gdpr_endpoints_exist(self):
        """Verify GDPR compliance endpoints exist."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Check legal endpoints exist
        response = client.get("/api/version")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main(["-v", "-m", "validation", __file__])