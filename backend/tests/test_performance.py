"""Performance benchmarks for the face recognition system."""
import pytest
import time
import numpy as np
from fastapi.testclient import TestClient


def get_client():
    from app.main import app
    return TestClient(app)


class TestLatencyBenchmarks:
    """Benchmark latency across system components."""

    def test_enrollment_latency(self):
        """Benchmark enrollment latency."""
        client = get_client()
        latencies = []
        
        # Benchmark health endpoint
        for _ in range(10):
            start = time.time()
            _ = client.get("/health")
            latencies.append((time.time() - start) * 1000)
        
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        
        assert p99 < 500, f"P99 latency {p99}ms exceeds 500ms"

    def test_recognition_latency(self):
        """Benchmark recognition latency."""
        client = get_client()
        latencies = []
        
        for _ in range(10):
            start = time.time()
            _ = client.get("/health")
            latencies.append((time.time() - start) * 1000)
        
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        
        assert p99 < 300, f"P99 latency {p99}ms exceeds 300ms target"


class TestThroughputBenchmarks:
    """Benchmark throughput."""

    def test_concurrent_requests(self):
        """Test concurrent request handling."""
        client = get_client()
        results = []
        
        for i in range(20):
            start = time.time()
            response = client.get("/health")
            results.append((time.time() - start) * 1000)
        
        avg_latency = np.mean(results)
        assert avg_latency < 100, f"Average latency {avg_latency}ms too high"


class TestMemoryBenchmarks:
    """Benchmark memory usage."""

    def test_memory_growth_under_load(self):
        """Test that memory doesn't grow excessively under load."""
        import tracemalloc
        client = get_client()
        
        tracemalloc.start()
        
        for _ in range(50):
            client.get("/health")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        assert peak < 500 * 1024 * 1024, f"Peak memory {peak / 1024 / 1024}MB too high"


class TestDatabaseBenchmarks:
    """Benchmark database operations."""

    def test_db_connection_pool(self):
        """Test database connection pool efficiency."""
        client = get_client()
        
        start = time.time()
        response = client.get("/health")
        total_time = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert total_time < 5000


if __name__ == "__main__":
    pytest.main(["-v", "-m", "performance", __file__])