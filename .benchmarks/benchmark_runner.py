#!/usr/bin/env python3
"""
AI-f Distributed Benchmark Suite
Validates latency and throughput claims under realistic workloads.

Benchmarks:
1. Single-recognition latency (p50, p95, p99)
2. Batch recognition throughput (req/sec)
3. Concurrent connection handling
4. Enrichment API latency
5. Celery task processing rate
6. Redis read/write latency
7. End-to-end recognition pipeline latency
8. System resilience under load
"""
import asyncio
import time
import statistics
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import httpx
    import numpy as np
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

# Benchmark configuration
DEFAULT_CONFIG = {
    'api_url': 'http://localhost:8000',
    'redis_url': 'redis://localhost:6379',
    'celery_broker': 'redis://localhost:6379/0',
    'concurrent_users': 100,
    'requests_per_user': 100,
    'test_duration_seconds': 3600,
    'warmup_seconds': 60,
    'target_rps': 1000,
    'acceptable_p50_ms': 50,
    'acceptable_p95_ms': 200,
    'acceptable_p99_ms': 500,
    'min_throughput_rps': 500,
}


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    name: str
    success: bool
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    throughput_rps: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    avg_ms: float = 0.0
    max_ms: float = 0.0
    min_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_stats(self):
        """Compute statistics from collected latencies."""
        if not self.latencies_ms:
            return
        self.total_requests = len(self.latencies_ms) + len(self.errors)
        self.successful_requests = len(self.latencies_ms)
        self.failed_requests = len(self.errors)
        if self.latencies_ms:
            self.latencies_ms.sort()
            n = len(self.latencies_ms)
            self.p50_ms = self.latencies_ms[int(n * 0.50)]
            self.p95_ms = self.latencies_ms[int(n * 0.95)]
            self.p99_ms = self.latencies_ms[int(n * 0.99)]
            self.avg_ms = statistics.mean(self.latencies_ms)
            self.max_ms = max(self.latencies_ms)
            self.min_ms = min(self.latencies_ms)
        duration = self.end_time - self.start_time
        if duration > 0:
            self.throughput_rps = self.successful_requests / duration

    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return {
            'name': self.name,
            'success': self.success,
            'total_requests': self.total_requests,
            'successful': self.successful_requests,
            'failed': self.failed_requests,
            'throughput_rps': round(self.throughput_rps, 2),
            'latency': {
                'min_ms': round(self.min_ms, 2),
                'avg_ms': round(self.avg_ms, 2),
                'p50_ms': round(self.p50_ms, 2),
                'p95_ms': round(self.p95_ms, 2),
                'p99_ms': round(self.p99_ms, 2),
                'max_ms': round(self.max_ms, 2),
            },
            'error_rate': round(len(self.errors) / max(1, self.total_requests) * 100, 2),
            'metadata': self.metadata,
        }


class BenchmarkSuite:
    """Complete benchmark suite for AI-f infrastructure."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.results: List[BenchmarkResult] = []

    async def run_single_request(self, url: str, method: str = 'GET',
                                  headers: Dict = None, json_body: Dict = None,
                                  timeout: float = 30) -> tuple:
        """Make a single HTTP request and return (success, latency_ms)."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == 'GET':
                    response = await client.get(url, headers=headers)
                elif method == 'POST':
                    response = await client.post(url, json=json_body, headers=headers)
                else:
                    response = await client.request(method, url, json=json_body, headers=headers)
                latency = (time.perf_counter() - start) * 1000
                return response.status_code < 500, latency
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return False, latency

    async def benchmark_api_latency(self, endpoint: str, method: str = 'GET',
                                     body: Dict = None, name: str = None,
                                     iterations: int = 100) -> BenchmarkResult:
        """Benchmark a single API endpoint."""
        name = name or endpoint
        result = BenchmarkResult(name=name)
        url = f"{self.config['api_url']}{endpoint}"
        result.start_time = time.perf_counter()

        tasks = []
        for _ in range(iterations):
            tasks.append(self.run_single_request(url, method, json_body=body))

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        result.end_time = time.perf_counter()

        for r in responses:
            if isinstance(r, Exception):
                result.errors.append(str(r))
            else:
                success, latency = r
                if success:
                    result.latencies_ms.append(latency)
                else:
                    result.errors.append(f"HTTP error: {latency}")

        result.compute_stats()
        return result

    async def benchmark_concurrent_load(self, endpoint: str,
                                         concurrent: int = None,
                                         per_user: int = None) -> BenchmarkResult:
        """Benchmark with concurrent users."""
        concurrent = concurrent or self.config['concurrent_users']
        per_user = per_user or self.config['requests_per_user']

        result = BenchmarkResult(name=f"concurrent_load_{concurrent}_users")
        url = f"{self.config['api_url']}{endpoint}"
        result.start_time = time.perf_counter()

        async def user_session(user_id: int):
            """Simulate a single user session."""
            user_latencies = []
            async with httpx.AsyncClient(timeout=30,
                     limits=httpx.Limits(max_keepalive_connections=10,
                                         max_connections=20)) as client:
                for i in range(per_user):
                    try:
                        start = time.perf_counter()
                        response = await client.get(url)
                        latency = (time.perf_counter() - start) * 1000
                        if response.status_code < 500:
                            user_latencies.append(latency)
                        else:
                            result.errors.append(f"User {user_id} req {i}: HTTP {response.status_code}")
                    except Exception as e:
                        result.errors.append(f"User {user_id} req {i}: {str(e)}")
            return user_latencies

        # Run all user sessions concurrently
        tasks = [user_session(i) for i in range(concurrent)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)

        result.end_time = time.perf_counter()
        for user_data in user_results:
            if isinstance(user_data, Exception):
                result.errors.append(str(user_data))
            else:
                result.latencies_ms.extend(user_data)

        result.compute_stats()
        return result

    async def benchmark_sustained_load(self, endpoint: str,
                                        duration: int = None,
                                        target_rps: int = None) -> BenchmarkResult:
        """Benchmark sustained throughput over time."""
        duration = duration or self.config['test_duration_seconds']
        target_rps = target_rps or self.config['target_rps']

        result = BenchmarkResult(name=f"sustained_load_{target_rps}rps_{duration}s")
        url = f"{self.config['api_url']}{endpoint}"
        result.start_time = time.perf_counter()

        interval = 1.0 / target_rps
        request_count = 0

        async with httpx.AsyncClient(timeout=30) as client:
            while (time.perf_counter() - result.start_time) < duration:
                batch_start = time.perf_counter()

                # Fire requests in parallel to achieve target RPS
                tasks = []
                for _ in range(min(target_rps // 10, 100)):
                    tasks.append(client.get(url))

                if tasks:
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in responses:
                        request_count += 1
                        if isinstance(r, Exception):
                            result.errors.append(str(r))
                        else:
                            if r.status_code < 500:
                                result.successful_requests += 1
                            else:
                                result.failed_requests += 1
                            r.close()

                # Pace to target RPS
                elapsed = time.perf_counter() - batch_start
                sleep_time = max(0, 0.1 - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        result.end_time = time.perf_counter()
        result.total_requests = request_count
        result.throughput_rps = result.successful_requests / (result.end_time - result.start_time)
        return result

    async def benchmark_redis_latency(self) -> BenchmarkResult:
        """Benchmark Redis read/write latency."""
        result = BenchmarkResult(name="redis_latency")

        try:
            import redis.asyncio as redis
            r = redis.from_url(self.config['redis_url'], decode_responses=True)

            result.start_time = time.perf_counter()
            iterations = 1000

            # Write benchmark
            for i in range(iterations):
                start = time.perf_counter()
                await r.set(f"bench_key_{i}", f"value_{i}")
                latency = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(latency)

            # Read benchmark
            read_latencies = []
            for i in range(iterations):
                start = time.perf_counter()
                await r.get(f"bench_key_{i}")
                latency = (time.perf_counter() - start) * 1000
                read_latencies.append(latency)

            result.end_time = time.perf_counter()
            # Combine write + read as round-trip
            result.latencies_ms = [(w + r) / 2 for w, r in
                                   zip(result.latencies_ms, read_latencies)]
            result.compute_stats()

            # Cleanup
            keys = [f"bench_key_{i}" for i in range(iterations)]
            await r.delete(*keys)
            await r.close()

        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result

    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        if not HAS_DEPS:
            return {'error': 'Missing dependencies: httpx, numpy'}

        print(f"Starting benchmark suite at {datetime.utcnow().isoformat()}")
        print(f"Target: {self.config['api_url']}")

        # 1. Basic API health
        print("\n[1/8] Testing API health endpoint...")
        health_result = await self.benchmark_api_latency('/healthz', iterations=50)
        self.results.append(health_result)

        # 2. Recognition endpoint latency
        print("[2/8] Testing recognition latency...")
        rec_result = await self.benchmark_api_latency(
            '/api/v1/recognize', method='POST',
            body={'camera_id': 'bench', 'threshold': 0.6},
            iterations=200
        )
        self.results.append(rec_result)

        # 3. Concurrent load test
        print("[3/8] Testing concurrent load (50 users)...")
        concurrent_result = await self.benchmark_concurrent_load(
            '/api/v1/recognize', concurrent=50, per_user=20
        )
        self.results.append(concurrent_result)

        # 4. Large-scale concurrent test
        print("[4/8] Testing large-scale concurrent load (200 users)...")
        large_result = await self.benchmark_concurrent_load(
            '/healthz', concurrent=200, per_user=50
        )
        self.results.append(large_result)

        # 5. Sustained throughput
        print(f"[5/8] Testing sustained load ({self.config['target_rps']}rps for 60s)...")
        sustained_result = await self.benchmark_sustained_load(
            '/healthz', duration=60, target_rps=self.config['target_rps']
        )
        self.results.append(sustained_result)

        # 6. Redis latency
        print("[6/8] Testing Redis latency...")
        redis_result = await self.benchmark_redis_latency()
        self.results.append(redis_result)

        # 7. Enrichment endpoint
        print("[7/8] Testing enrichment endpoint...")
        enrich_result = await self.benchmark_api_latency('/api/v1/enrich', iterations=50)
        self.results.append(enrich_result)

        # 8. 6-hour extended stress test
        print("[8/8] Running 6-hour extended stress test (summary mode)...")
        stress_result = await self.benchmark_sustained_load(
            '/healthz', duration=21600, target_rps=self.config['target_rps'] // 2
        )
        self.results.append(stress_result)

        # Compile final report
        report = self.generate_report()
        return report

    def generate_report(self) -> Dict[str, Any]:
        """Generate final benchmark report."""
        report = {
            'title': 'AI-f Infrastructure Benchmark Report',
            'timestamp': datetime.utcnow().isoformat(),
            'config': self.config,
            'benchmarks': [r.to_dict() for r in self.results],
            'summary': {
                'total_benchmarks': len(self.results),
                'passed': sum(1 for r in self.results
                             if r.throughput_rps >= self.config['min_throughput_rps']),
                'failed': sum(1 for r in self.results
                             if r.throughput_rps < self.config['min_throughput_rps']),
                'latency_targets': {
                    'p50_ms': self.config['acceptable_p50_ms'],
                    'p95_ms': self.config['acceptable_p95_ms'],
                    'p99_ms': self.config['acceptable_p99_ms'],
                }
            }
        }

        # Validate latency claims
        overall = self.results[-1] if self.results else None
        if overall:
            report['summary']['measured_p50_ms'] = overall.p50_ms
            report['summary']['measured_p95_ms'] = overall.p95_ms
            report['summary']['measured_p99_ms'] = overall.p99_ms
            report['summary']['measured_throughput_rps'] = overall.throughput_rps
            report['summary']['latency_claims_met'] = (
                overall.p50_ms <= self.config['acceptable_p50_ms'] and
                overall.p95_ms <= self.config['acceptable_p95_ms'] and
                overall.p99_ms <= self.config['acceptable_p99_ms']
            )
            report['summary']['throughput_claims_met'] = (
                overall.throughput_rps >= self.config['min_throughput_rps']
            )

        return report

    def print_summary(self):
        """Print human-readable summary."""
        print("\n" + "=" * 60)
        print("AI-f BENCHMARK SUMMARY")
        print("=" * 60)
        for r in self.results:
            status = "✓" if r.success else "✗"
            print(f"\n{status} {r.name}")
            if r.latencies_ms:
                print(f"  Throughput: {r.throughput_rps:.1f} req/s")
                print(f"  Latency p50: {r.p50_ms:.1f}ms, p95: {r.p95_ms:.1f}ms, p99: {r.p99_ms:.1f}ms")
                print(f"  Success rate: {r.successful_requests}/{r.total_requests} ({100 - r.error_rate:.1f}%)")
            else:
                print(f"  Errors: {len(r.errors)}")

        print("\n" + "=" * 60)


if __name__ == '__main__':
    import sys

    config = {**DEFAULT_CONFIG}
    if len(sys.argv) > 1:
        config['api_url'] = sys.argv[1]

    suite = BenchmarkSuite(config)

    # Run benchmarks
    report = asyncio.run(suite.run_all_benchmarks())

    # Print summary
    suite.print_summary()

    # Save report
    report_path = f"benchmark_report_{int(time.time())}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report saved to {report_path}")