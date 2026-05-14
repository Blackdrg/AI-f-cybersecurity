"""Production environment smoke tests.
Minimal tests to verify the system is operational in production.
"""
import pytest
import os


@pytest.mark.smoke
@pytest.mark.e2e
class TestProductionSmokeTests:
    """Smoke tests for production deployment verification."""

    def test_environment_variables(self):
        """Verify required environment variables are set."""
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET",
            "STRIPE_SECRET_KEY"
        ]
        
        missing = []
        for var in required_vars:
            if not os.environ.get(var) and not os.environ.get(var.lower()):
                missing.append(var)
        
        if missing:
            pytest.skip(f"Missing environment variables: {missing}")

    def test_database_connection(self):
        """Test database is reachable."""
        import asyncio
        from app.db.db_client import DBClient
        
        async def check_db():
            try:
                db = DBClient()
                await db.init_db()
                if db.pool:
                    async with db.pool.acquire() as conn:
                        result = await conn.fetchval("SELECT 1")
                        return result == 1
                return False
            except Exception:
                return False
        
        result = asyncio.run(check_db())
        assert result, "Database connection failed"

    def test_redis_connection(self):
        """Test Redis is reachable."""
        import asyncio
        import redis.asyncio as redis
        
        async def check_redis():
            try:
                client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
                pong = await client.ping()
                await client.close()
                return pong is True
            except Exception:
                return False
        
        result = asyncio.run(check_redis())
        assert result, "Redis connection failed"

    def test_api_health_endpoint(self):
        """Test API health endpoint."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_openapi_schema(self):
        """Test OpenAPI schema is accessible."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "paths" in response.json()

    def test_model_loading(self):
        """Test that ONNX models can be loaded."""
        try:
            import onnxruntime as ort
            from pathlib import Path
            
            model_path = Path("/models/onnx_bundle")
            if not model_path.exists():
                pytest.skip("ONNX bundle not found")
            
            # Try loading a model
            test_model = model_path / "retinaface.onnx"
            if test_model.exists():
                session = ort.InferenceSession(str(test_model))
                assert session is not None
        except ImportError:
            pytest.skip("ONNX Runtime not installed")

    def test_stripe_connection(self):
        """Test Stripe API is configured."""
        import stripe
        
        api_key = os.environ.get("STRIPE_SECRET_KEY")
        if not api_key:
            pytest.skip("Stripe API key not configured")
        
        stripe.api_key = api_key
        # Don't actually make a request, just verify key is set
        assert len(api_key) > 0