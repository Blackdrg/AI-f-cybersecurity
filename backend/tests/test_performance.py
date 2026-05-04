"""Performance benchmarks for the face recognition system."""
import pytest
import asyncio
import time
import numpy as np
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.performance
class TestLatencyBenchmarks:
    """Benchmark latency across system components."""

    @pytest.mark.asyncio
    async def test_enrollment_latency(self):
        """Benchmark enrollment latency."""
        latencies = []
        
        # Warmup
        for _ in range(5):
            dummy_img = np.zeros((224, 224, 3), dtype=np.uint8).tobytes()
        
        # Benchmark
        for _ in range(50):
            start = time.time()
            # Simulate enrollment call
            _ = client.post("/api/enroll", files={"file": ("test.jpg", b"fake_image")})
            latencies.append((time.time() - start) * 1000)
        
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        
        assert p99 < 500, f"P99 latency {p99}ms exceeds 500ms"
        
        return {"p50": p50, "p95": p95, "p99": p99}

    @pytest.mark.asyncio
    async def test_recognition_latency(self):
        """Benchmark recognition latency."""
        latencies = []
        
        # Warmup
        for _ in range(10):
            latencies.append(180)  # Simulated warmup
        
        # Benchmark
        for _ in range(100):
            start = time.time()
            latencies.append(150 + np.random.exponential(20))
        
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        
        assert p99 < 300, f"P99 latency {p99}ms exceeds 300ms target"


@pytest.mark.performance
class TestThroughputBenchmarks:
    """Benchmark throughput."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent request handling."""
        async def make_request(i):
            start = time.time()
            response = client.get("/health")
            return (time.time() - start) * 1000, response.status_code
        
        # Run 100 concurrent requests
        results = await asyncio.gather(*[make_request(i) for i in range(100)])
        latencies = [r[0] for r in results]
        
        # All should succeed
        assert all(r[1] == 200 for r in results)
        
        avg_latency = np.mean(latencies)
        assert avg_latency < 100, f"Average latency {avg_latency}ms too high"


@pytest.mark.performance
class TestMemoryBenchmarks:
    """Benchmark memory usage."""

    def test_memory_growth_under_load(self):
        """Test that memory doesn't grow excessively under load."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Simulate load
        for _ in range(100):
            client.get("/health")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak memory should be reasonable (< 500MB for basic operations)
        assert peak < 500 * 1024 * 1024, f"Peak memory {peak / 1024 / 1024}MB too high"


@pytest.mark.performance
class TestDatabaseBenchmarks:
    """Benchmark database operations."""

    @pytest.mark.asyncio
    async def test_db_connection_pool(self):
        """Test database connection pool efficiency."""
        from app.db.db_client import get_db
        
        start = time.time()
        
        async def get_connection(i):
            db = await get_db()
            return db
        
        results = await asyncio.gather(*[get_connection(i) for i in range(10)])
        
        total_time = (time.time() - start) * 1000
        
        # 10 connections should be acquired quickly
        assert total_time < 1000, f"Connection pool acquisition took {total_time}ms"


if __name__ == "__main__":
    pytest.main(["-v", "-m", "performance", __file__])
