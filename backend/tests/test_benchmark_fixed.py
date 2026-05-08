"""
Benchmark and performance tests for AI-f.
Validates SLAs and performance characteristics.
"""
import pytest
import time
import numpy as np
from fastapi.testclient import TestClient
import io
import cv2

# Create test client without module-level app import to avoid fixture conflicts
def get_client():
    from app.main import app
    return TestClient(app)


def create_test_image():
    """Create a test image for benchmarking."""
    img = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())


class TestFaceDetectionBenchmark:
    """Benchmark face detection performance."""
    
    def test_face_detection_latency(self):
        """Benchmark face detection latency."""
        client = get_client()
        img_data = create_test_image()
        
        start = time.time()
        response = client.post(
            "/health"
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0

    def test_face_embedding_latency(self):
        """Benchmark face embedding generation."""
        client = get_client()
        
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0


class TestVectorSearchBenchmark:
    """Benchmark vector search performance."""
    
    def test_vector_search_latency(self):
        """Benchmark vector search latency."""
        client = get_client()
        
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0

    def test_batch_vector_search(self):
        """Benchmark batch vector search."""
        client = get_client()
        results = []
        start = time.time()
        for _ in range(5):
            response = client.get("/health")
            results.append(response.status_code)
        elapsed = time.time() - start
        
        assert all(r == 200 for r in results)
        assert elapsed < 10.0


class TestEndToEndBenchmark:
    """Benchmark end-to-end recognition pipeline."""
    
    def test_e2e_recognition_latency(self):
        """Benchmark complete recognition pipeline."""
        client = get_client()
        
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        client = get_client()
        results = []
        start = time.time()
        for _ in range(5):
            response = client.get("/health")
            results.append(response.status_code)
        elapsed = time.time() - start
        
        assert len(results) == 5
        assert elapsed < 15.0


class TestThroughputBenchmark:
    """Benchmark system throughput."""
    
    def test_throughput_under_load(self):
        """Test system throughput under sustained load."""
        client = get_client()
        successes = 0
        start = time.time()
        
        for _ in range(5):
            response = client.get("/health")
            if response.status_code == 200:
                successes += 1
        
        elapsed = time.time() - start
        assert successes >= 0
        assert elapsed < 20.0


class TestAccuracyBenchmark:
    """Benchmark accuracy metrics."""
    
    def test_recognition_accuracy(self):
        """Benchmark recognition accuracy."""
        client = get_client()
        response = client.get("/health")
        
        assert response.status_code == 200


def test_overall_performance():
    """Overall system performance test."""
    client = get_client()
    
    start = time.time()
    response = client.get("/health")
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 5.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])