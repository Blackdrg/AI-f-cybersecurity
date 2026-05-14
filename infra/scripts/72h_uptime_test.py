#!/usr/bin/env python3
"""
AI-f 72-Hour Uptime Test
Validates production infrastructure stability over 72 hours.

Run: python 72h_uptime_test.py --config uptime_config.json
"""
import asyncio
import time
import json
import os
import logging
import subprocess
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceCheck:
    name: str
    check_fn_name: str
    interval_seconds: int = 60
    consecutive_failures: int = 0
    total_checks: int = 0
    successful_checks: int = 0
    failures: List[Dict] = field(default_factory=list)
    is_critical: bool = True


class UptimeTestRunner:
    """72-hour uptime test for AI-f production infrastructure."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.start_time = None
        self.duration_hours = config.get('duration_hours', 72)
        self.check_interval = config.get('check_interval_seconds', 60)
        self.alert_threshold = config.get('alert_failure_threshold', 3)

        # API endpoints to check
        self.api_endpoints = config.get('api_endpoints', [
            {'url': '/healthz', 'name': 'health', 'critical': True},
            {'url': '/api/v1/status', 'name': 'api_status', 'critical': True},
            {'url': '/api/v1/metrics', 'name': 'metrics', 'critical': False},
            {'url': '/api/v1/persons/count', 'name': 'person_count', 'critical': False},
        ])

        # Service checks
        self.services: List[ServiceCheck] = [
            ServiceCheck('postgres', 'check_postgres', 120, is_critical=True),
            ServiceCheck('redis', 'check_redis', 60, is_critical=True),
            ServiceCheck('celery_workers', 'check_celery_workers', 120, is_critical=True),
            ServiceCheck('backend_api', 'check_backend_api', 30, is_critical=True),
            ServiceCheck('prometheus', 'check_prometheus', 300, is_critical=False),
            ServiceCheck('grafana', 'check_grafana', 300, is_critical=False),
            ServiceCheck('nginx', 'check_nginx', 60, is_critical=True),
        ]

        # Metrics tracking
        self.metrics_history = deque(maxlen=10000)
        self.alert_history: List[Dict] = []
        self.total_checks = 0
        self.total_failures = 0
        self.api_latencies: List[float] = []
        self.start_time = datetime.utcnow()
        self.test_passed = True

    async def check_postgres(self) -> bool:
        """Check PostgreSQL connectivity and health."""
        try:
            import asyncpg
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = int(os.getenv('DB_PORT', 5432))
            db_user = os.getenv('DB_USER', 'postgres')
            db_pass = os.getenv('DB_PASSWORD', 'password')
            db_name = os.getenv('DB_NAME', 'face_recognition')

            conn = await asyncpg.connect(
                host=db_host, port=db_port, user=db_user,
                password=db_pass, database=db_name, timeout=10
            )
            await conn.execute("SELECT 1")

            # Check replication lag
            lag = await conn.fetchval("""
                SELECT COALESCE(
                    EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::float, 0
                )
            """)

            pool_size = await conn.fetchval(
                "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
            )

            await conn.close()

            self.metrics_history.append({
                'service': 'postgres',
                'timestamp': datetime.utcnow().isoformat(),
                'replication_lag': lag,
                'active_connections': pool_size,
            })

            return True
        except Exception as e:
            logger.error(f"PostgreSQL check failed: {e}")
            return False

    async def check_redis(self) -> bool:
        """Check Redis connectivity and health."""
        try:
            import redis.asyncio as redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url, decode_responses=True)

            start = time.perf_counter()
            await r.ping()
            latency = (time.perf_counter() - start) * 1000

            info = await r.info('memory')
            memory_used = info.get('used_memory', 0)

            self.metrics_history.append({
                'service': 'redis',
                'timestamp': datetime.utcnow().isoformat(),
                'latency_ms': latency,
                'memory_used': memory_used,
            })

            await r.close()
            return True
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            return False

    async def check_celery_workers(self) -> bool:
        """Check Celery workers are responsive."""
        try:
            from celery import Celery
            from app.celery import celery_app

            inspect = celery_app.control.inspect(timeout=10)
            active = inspect.active()
            stats = inspect.stats()

            if active is None or stats is None:
                logger.warning("No Celery workers responding")
                return False

            worker_count = len(stats)
            active_task_count = sum(len(tasks) for tasks in (active or {}).values())

            self.metrics_history.append({
                'service': 'celery',
                'timestamp': datetime.utcnow().isoformat(),
                'worker_count': worker_count,
                'active_tasks': active_task_count,
            })
            return True
        except Exception as e:
            logger.error(f"Celery check failed: {e}")
            return False

    async def check_backend_api(self) -> bool:
        """Check backend API endpoints."""
        all_passed = True
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                for endpoint in self.api_endpoints:
                    try:
                        start = time.perf_counter()
                        response = await client.get(
                            f"{self.config.get('api_url', 'http://localhost:8000')}{endpoint['url']}"
                        )
                        latency = (time.perf_counter() - start) * 1000
                        self.api_latencies.append(latency)

                        if response.status_code != 200:
                            all_passed = False
                            if endpoint['critical']:
                                logger.error(f"API {endpoint['name']} returned {response.status_code}")
                    except Exception as e:
                        all_passed = False
                        logger.error(f"API {endpoint['name']} check failed: {e}")

        except Exception as e:
            all_passed = False
            logger.error(f"Backend API check failed: {e}")

        return all_passed

    async def check_prometheus(self) -> bool:
        """Check Prometheus is scraping."""
        try:
            import httpx
            url = self.config.get('prometheus_url', 'http://localhost:9090')
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{url}/api/v1/targets")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Prometheus check failed: {e}")
            return False

    async def check_grafana(self) -> bool:
        """Check Grafana is accessible."""
        try:
            import httpx
            url = self.config.get('grafana_url', 'http://localhost:3001')
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{url}/api/health")
                return response.status_code == 200
        except Exception:
            return False

    async def check_nginx(self) -> bool:
        """Check NGINX is serving."""
        try:
            import httpx
            url = self.config.get('nginx_url', 'http://localhost/healthz')
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False

    async def run_single_check_cycle(self) -> Dict[str, Any]:
        """Run all service checks once."""
        self.total_checks += 1
        cycle_results = {}
        cycle_time = datetime.utcnow().isoformat()

        for service in self.services:
            check_fn = getattr(self, service.check_fn_name)
            try:
                passed = await check_fn()
                cycle_results[service.name] = passed
                service.total_checks += 1

                if passed:
                    service.successful_checks += 1
                    service.consecutive_failures = 0
                else:
                    service.consecutive_failures += 1
                    self.total_failures += 1
                    service.failures.append({
                        'time': cycle_time,
                        'consecutive': service.consecutive_failures,
                    })

                    if service.consecutive_failures >= self.alert_threshold:
                        self.test_passed = False
                        alert = {
                            'service': service.name,
                            'severity': 'CRITICAL' if service.is_critical else 'WARNING',
                            'consecutive_failures': service.consecutive_failures,
                            'time': cycle_time,
                        }
                        self.alert_history.append(alert)
                        logger.critical(f"ALERT: {service.name} failed {service.consecutive_failures} times")

            except Exception as e:
                logger.error(f"Check {service.name} raised: {e}")
                cycle_results[service.name] = False

        return cycle_results

    async def run(self) -> Dict[str, Any]:
        """Run the full 72-hour uptime test."""
        logger.info(f"Starting {self.duration_hours}h uptime test at {self.start_time}")

        end_time = self.start_time + timedelta(hours=self.duration_hours)
        cycle_count = 0
        report_interval = 300  # Print status every 5 minutes
        last_report = time.time()

        while datetime.utcnow() < end_time:
            cycle_count += 1
            await self.run_single_check_cycle()

            # Periodic status update
            if time.time() - last_report >= report_interval:
                self.print_status()
                last_report = time.time()

            # Sleep until next check
            await asyncio.sleep(self.check_interval)

        # Final report
        return self.generate_report()

    def print_status(self):
        """Print current status."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() / 3600
        api_avg_latency = statistics.mean(self.api_latencies[-100:]) if self.api_latencies else 0

        logger.info(
            f"[{elapsed:.1f}h] Cycles: {self.total_checks} | "
            f"Failures: {self.total_failures} | "
            f"API avg latency: {api_avg_latency:.1f}ms | "
            f"Status: {'PASS' if self.test_passed else 'FAIL'}"
        )

        for svc in self.services:
            status = "✓" if svc.consecutive_failures == 0 else f"✗ ({svc.consecutive_failures})"
            rate = (svc.successful_checks / max(1, svc.total_checks)) * 100
            logger.info(f"  {svc.name}: {status} uptime={rate:.1f}%")

    def generate_report(self) -> Dict[str, Any]:
        """Generate final uptime test report."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        hours_elapsed = elapsed / 3600

        api_avg = statistics.mean(self.api_latencies) if self.api_latencies else 0
        api_p50 = sorted(self.api_latencies)[len(self.api_latencies) // 2] if self.api_latencies else 0
        api_p99 = sorted(self.api_latencies)[int(len(self.api_latencies) * 0.99)] if self.api_latencies else 0

        service_uptime = {}
        for svc in self.services:
            rate = (svc.successful_checks / max(1, svc.total_checks)) * 100
            service_uptime[svc.name] = {
                'uptime_percent': round(rate, 3),
                'total_checks': svc.total_checks,
                'successful': svc.successful_checks,
                'consecutive_failures': svc.consecutive_failures,
                'is_critical': svc.is_critical,
                'passed': rate >= 99.9,
            }

        overall_pass = (
            self.test_passed and
            all(svc.successful_checks / max(1, svc.total_checks) >= 0.999
                for svc in self.services if svc.is_critical)
        )

        report = {
            'test_type': '72h_continuous_uptime',
            'overall_result': 'PASS' if overall_pass else 'FAIL',
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'duration_hours': round(hours_elapsed, 2),
            'total_check_cycles': self.total_checks,
            'total_failures': self.total_failures,
            'api_metrics': {
                'avg_latency_ms': round(api_avg, 2),
                'p50_latency_ms': round(api_p50, 2),
                'p99_latency_ms': round(api_p99, 2),
                'total_requests': len(self.api_latencies),
            },
            'services': service_uptime,
            'alerts': self.alert_history,
        }

        return report

    def save_report(self, filepath: str = None):
        """Save report to JSON file."""
        report = self.generate_report()
        filepath = filepath or f"uptime_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {filepath}")
        return filepath


async def quick_test(duration_minutes: int = 5):
    """Quick sanity check - run for a few minutes."""
    config = {
        'api_url': os.getenv('API_URL', 'http://localhost:8000'),
        'duration_hours': duration_minutes / 60,
        'check_interval_seconds': 30,
        'alert_failure_threshold': 2,
    }

    runner = UptimeTestRunner(config)
    report = await runner.run()

    # Print summary
    print("\n" + "=" * 60)
    print("UPTIME TEST SUMMARY")
    print("=" * 60)
    print(f"Duration: {report['duration_hours']:.2f}h")
    print(f"Total cycles: {report['total_check_cycles']}")
    print(f"Total failures: {report['total_failures']}")
    print(f"Overall result: {report['overall_result']}")

    for svc_name, svc_data in report['services'].items():
        icon = "✓" if svc_data['passed'] else "✗"
        print(f"  {icon} {svc_name}: {svc_data['uptime_percent']:.3f}% uptime")

    print(f"\nAPI Metrics:")
    print(f"  Avg latency: {report['api_metrics']['avg_latency_ms']:.1f}ms")
    print(f"  P50 latency: {report['api_metrics']['p50_latency_ms']:.1f}ms")
    print(f"  P99 latency: {report['api_metrics']['p99_latency_ms']:.1f}ms")

    runner.save_report()
    return report


if __name__ == '__main__':
    import statistics
    import argparse

    parser = argparse.ArgumentParser(description='AI-f 72-hour uptime test')
    parser.add_argument('--hours', type=int, default=72, help='Test duration in hours')
    parser.add_argument('--quick', action='store_true', help='Run 5-minute quick test')
    parser.add_argument('--config', type=str, help='Config JSON file')
    args = parser.parse_args()

    if args.quick:
        asyncio.run(quick_test(5))
    else:
        config = DEFAULT_CONFIG.copy() if 'DEFAULT_CONFIG' in dir() else {}
        if args.config:
            with open(args.config) as f:
                config = json.load(f)
        config.setdefault('duration_hours', args.hours)

        runner = UptimeTestRunner(config)
        report = asyncio.run(runner.run())
        runner.save_report()