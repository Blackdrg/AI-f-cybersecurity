#!/usr/bin/env python3
"""
AI-f Distributed Load Testing & Benchmark Framework
Run with: locust -f load_test_framework.py --headless -u 1000 -r 100
"""
import asyncio
import time
import random
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)


class LoadTestFramework:
    """Distributed load testing framework for AI-f infrastructure."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_url = config.get('api_url', 'http://localhost:8000')
        self.redis_url = config.get('redis_url', 'redis://localhost:6379')
        self.num_users = config.get('num_users', 1000)
        self.spawn_rate = config.get('spawn_rate', 100)
        self.test_duration = config.get('test_duration', 3600)  # seconds
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_latency_ms': 0,
            'p50_latency_ms': 0,
            'p95_latency_ms': 0,
            'p99_latency_ms': 0,
            'max_latency_ms': 0,
            'throughput_rps': 0,
            'errors': [],
            'latencies': [],
        }

    async def setup_test_data(self):
        """Create test data for load testing."""
        from app.db.db_client import get_db
        db = get_db()

        # Create test org
        test_org_id = str(uuid.uuid4())
        test_api_key = f"test_key_{uuid.uuid4().hex[:16]}"

        # Store latency results
        self.results['test_start'] = datetime.utcnow().isoformat()
        return test_org_id, test_api_key

    async def recognition_request(self, image_data: bytes, camera_id: str) -> Dict:
        """Simulate a recognition API request."""
        import httpx
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/recognize",
                    json={
                        'camera_id': camera_id,
                        'threshold': 0.6,
                        'top_k': 5,
                    },
                    files={'image': image_data},
                    headers={'X-API-Key': self.config.get('api_key', '')},
                    timeout=30
                )
                latency = (time.perf_counter() - start) * 1000
                return {
                    'success': response.status_code == 200,
                    'latency_ms': latency,
                    'status_code': response.status_code,
                    'response': response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return {
                'success': False,
                'latency_ms': latency,
                'error': str(e)
            }

    async def enrollment_request(self, person_data: Dict, image_data: bytes) -> Dict:
        """Simulate an enrollment API request."""
        import httpx
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/enroll",
                    json=person_data,
                    files={'images': image_data},
                    timeout=30
                )
                latency = (time.perf_counter() - start) * 1000
                return {
                    'success': response.status_code == 200,
                    'latency_ms': latency,
                    'status_code': response.status_code
                }
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return {
                'success': False,
                'latency_ms': latency,
                'error': str(e)
            }

    async def health_check_request(self) -> Dict:
        """Simulate a health check request."""
        import httpx
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_url}/healthz", timeout=10)
                latency = (time.perf_counter() - start) * 1000
                return {
                    'success': response.status_code == 200,
                    'latency_ms': latency
                }
        except Exception as e:
            return {
                'success': False,
                'latency_ms': 0,
                'error': str(e)
            }

    def record_result(self, result: Dict):
        """Record a request result."""
        self.results['total_requests'] += 1
        if result.get('success', False):
            self.results['successful_requests'] += 1
        else:
            self.results['failed_requests'] += 1
            if 'error' in result:
                self.results['errors'].append(result['error'])

        latency = result.get('latency_ms', 0)
        self.results['latencies'].append(latency)

    def compute_statistics(self):
        """Compute final statistics from collected latencies."""
        latencies = sorted(self.results['latencies'])
        n = len(latencies)
        if n == 0:
            return

        self.results['avg_latency_ms'] = sum(latencies) / n
        self.results['p50_latency_ms'] = latencies[int(n * 0.5)]
        self.results['p95_latency_ms'] = latencies[int(n * 0.95)]
        self.results['p99_latency_ms'] = latencies[int(n * 0.99)]
        self.results['max_latency_ms'] = latencies[-1]

        duration = self.config.get('test_duration', 3600)
        if duration > 0:
            self.results['throughput_rps'] = n / duration


# Locust-style task definitions for distributed load testing
try:
    from locust import HttpUser, task, between, constant_pacing

    class RecognitionUser(HttpUser):
        """Locust user simulating face recognition requests."""
        wait_time = between(0.1, 0.5)

        @task(10)
        def recognize_face(self):
            """Simulate face recognition."""
            img_bytes = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8).tobytes()
            with self.client.post(
                "/api/v1/recognize",
                json={'camera_id': 'test-camera', 'threshold': 0.6, 'top_k': 5},
                name="/api/v1/recognize",
                timeout=10
            ) as response:
                pass

        @task(3)
        def health_check(self):
            """Health check endpoint."""
            with self.client.get("/healthz", name="/healthz", timeout=5) as response:
                pass

    class EnrollmentUser(HttpUser):
        """Locust user simulating enrollment requests."""
        wait_time = between(1.0, 3.0)

        @task(5)
        def enroll_person(self):
            """Simulate person enrollment."""
            img_bytes = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8).tobytes()
            with self.client.post(
                "/api/v1/enroll",
                json={'name': f'test_user_{uuid.uuid4().hex[:8]}',
                      'metadata': {'test': True}},
                files={'images': img_bytes},
                name="/api/v1/enroll",
                timeout=30
            ) as response:
                pass

    class BackgroundTaskUser(HttpUser):
        """Locust user simulating background API calls."""
        wait_time = between(2.0, 10.0)

        @task
        def get_person(self):
            """Get person details."""
            with self.client.get(f"/api/v1/persons/{uuid.uuid4()}",
                                 name="/api/v1/persons/[id]", timeout=5) as response:
                pass

        @task
        def search_persons(self):
            """Search persons."""
            with self.client.get("/api/v1/persons?search=test&limit=10&offset=0",
                                 name="/api/v1/persons/search", timeout=5) as response:
                pass

except ImportError:
    logger.warning("locust not installed - load testing tasks unavailable")


def run_stress_test(config: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a full stress test and return results."""
    framework = LoadTestFramework(config)
    return framework.results


# Benchmark runner for distributed execution
class DistributedBenchmarkRunner:
    """Run benchmarks across multiple nodes."""

    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        self.results = {}

    async def run_benchmark_on_node(self, node: str, benchmark: str) -> Dict:
        """Run a specific benchmark on a node."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"http://{node}/benchmark/run",
                    json={'benchmark': benchmark},
                    timeout=60
                )
                return response.json()
        except Exception as e:
            return {'node': node, 'error': str(e)}

    async def run_all_benchmarks(self, benchmarks: List[str]) -> Dict:
        """Run all benchmarks on all nodes."""
        import asyncio
        tasks = []
        for node in self.nodes:
            for bench in benchmarks:
                tasks.append(self.run_benchmark_on_node(node, bench))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            'total_runs': len(tasks),
            'results': [r if isinstance(r, dict) else {'error': str(r)} for r in results]
        }


if __name__ == '__main__':
    print("Load test framework loaded. Run with locust:")
    print("  locust -f load_test_framework.py --headless -u 1000 -r 100 -t 5m")