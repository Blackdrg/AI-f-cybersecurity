#!/usr/bin/env python3
"""
AI-f Infrastructure Validation Suite
Validates all production infrastructure after deployment.
"""
import sys
import os
import asyncio
import json
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

SECTIONS = {
    'postgres': '🐘 PostgreSQL',
    'redis': '🔴 Redis',
    'redis_sentinel': '🛡️ Redis Sentinel',
    'api': '🚀 Backend API',
    'celery': '🌿 Celery Workers',
    'celery_beat': '⏰ Celery Beat',
    'celery_flower': '🌺 Celery Flower',
    'pgpool': '🔄 PgPool-II',
    'prometheus': '📊 Prometheus',
    'grafana': '📈 Grafana',
    'nginx': '🌐 NGINX',
    'faiss': '⚡ FAISS',
    'database_schema': '📋 Database Schema',
    'security': '🔒 Security',
}


class CheckResult:
    def __init__(self, name: str, passed: bool, message: str = '', details: dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            'name': self.name,
            'passed': self.passed,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
        }


class InfrastructureValidator:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.results: list[CheckResult] = []
        self.sections = {}

    def check(self, section: str, name: str, passed: bool,
              message: str = '', details: dict = None):
        result = CheckResult(name, passed, message, details)
        self.results.append(result)
        if section not in self.sections:
            self.sections[section] = []
        self.sections[section].append(result)
        icon = '✅' if passed else '❌'
        print(f"  {icon} {name}: {message}")

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': round(passed / total * 100, 1) if total else 0,
            'timestamp': datetime.utcnow().isoformat(),
            'sections': {k: len([r for r in v if r.passed]) for k, v in self.sections.items()},
        }


async def main():
    print("=" * 70)
    print("  AI-f Infrastructure Validation Suite")
    print("=" * 70)
    print()

    validator = InfrastructureValidator()

    # --- PostgreSQL Check ---
    print("🐘 PostgreSQL")
    try:
        import asyncpg
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', 5432))
        db_user = os.getenv('DB_USER', 'postgres')

        conn = await asyncpg.connect(
            host=db_host, port=db_port, user=db_user,
            password=os.getenv('DB_PASSWORD', 'password'),
            database=os.getenv('DB_NAME', 'face_recognition'),
            timeout=10
        )

        # Version
        version = await conn.fetchval("SELECT version()")
        validator.check('postgres', 'PostgreSQL Version', True,
                        version.split(',')[0] if version else 'Unknown')

        # Extensions
        exts = await conn.fetch("SELECT extname FROM pg_extension")
        ext_list = [r['extname'] for r in exts]
        for ext in ['vector', 'uuid-ossp', 'pgcrypto', 'pg_stat_statements']:
            validator.check('postgres', f'Extension: {ext}',
                            ext in ext_list,
                            'Enabled' if ext in ext_list else 'Missing')

        # Table count
        table_count = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog','information_schema','pg_toast')"
        )
        validator.check('postgres', 'Table Count', table_count >= 40,
                        f'{table_count} tables found',
                        {'count': table_count, 'minimum': 40})

        # RLS enabled
        rls_count = await conn.fetchval("""
            SELECT COUNT(*) FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relrowsecurity = true
            AND n.nspname NOT IN ('pg_catalog','information_schema')
        """)
        validator.check('postgres', 'RLS Tables', rls_count >= 30,
                        f'RLS on {rls_count} tables')

        # Vector index
        has_hnsw = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_indexes WHERE indexname LIKE '%hnsw%'"
        )
        validator.check('postgres', 'Vector Indexes', has_hnsw > 0,
                        f'{has_hnsw} HNSW indexes found')

        # Performance indexes
        perf_indexes = await conn.fetchval("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE indexname IN (
                'idx_recog_events_org_time', 'idx_persons_org_name',
                'idx_alerts_org_severity', 'idx_cameras_org_status'
            )
        """)
        validator.check('postgres', 'Performance Indexes', perf_indexes >= 4,
                        f'{perf_indexes} performance indexes found')

        # Connection pool stats
        active_conns = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
        )
        max_conns = await conn.fetchval("SHOW max_connections")
        validator.check('postgres', 'Connections', True,
                        f'{active_conns}/{max_conns} active',
                        {'active': active_conns, 'max': max_conns})

        await conn.close()
    except Exception as e:
        validator.check('postgres', 'Connection', False, str(e))

    # --- Redis Check ---
    print("\n🔴 Redis")
    try:
        import redis.asyncio as redis
        r = redis.from_url(
            os.getenv('REDIS_URL', 'redis://localhost:6379'),
            decode_responses=True
        )
        pong = await r.ping()
        info = await r.info('server')
        memory = await r.info('memory')

        validator.check('redis', 'Connection', pong,
                        f'Redis {info.get("redis_version", "?")}')
        validator.check('redis', 'Memory', True,
                        memory.get('used_memory_human', '?'))
        validator.check('redis', 'Max Memory', True,
                        memory.get('maxmemory_human', 'unlimited'))
        validator.check('redis', 'Clients', True,
                        f'{info.get("connected_clients", "?")} connected')
        validator.check('redis', 'Uptime', True,
                        f'{info.get("uptime_in_seconds", "?")}s')

        # Persistence check
        aof_enabled = info.get('aof_enabled', 0)
        validator.check('redis', 'AOF Persistence', bool(aof_enabled),
                        'Enabled' if aof_enabled else 'Disabled')

        await r.close()
    except Exception as e:
        validator.check('redis', 'Connection', False, str(e))

    # --- API Check ---
    print("\n🚀 Backend API")
    try:
        import httpx
        base_url = os.getenv('API_URL', 'http://localhost:8000')

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # Health endpoint
            try:
                r = await client.get(f'{base_url}/healthz')
                validator.check('api', 'Health Endpoint', r.status_code == 200,
                                f'HTTP {r.status_code}')
            except Exception as e:
                validator.check('api', 'Health Endpoint', False, str(e))

            # Metrics endpoint
            try:
                r = await client.get(f'{base_url}/metrics')
                validator.check('api', 'Metrics Endpoint', r.status_code == 200,
                                f'HTTP {r.status_code}')
            except Exception as e:
                validator.check('api', 'Metrics Endpoint', False, str(e))

            # Status endpoint
            try:
                r = await client.get(f'{base_url}/api/v1/status')
                validator.check('api', 'Status Endpoint', r.status_code == 200,
                                f'HTTP {r.status_code}')
            except Exception as e:
                validator.check('api', 'Status Endpoint', False, str(e))

            # Auth check
            try:
                r = await client.get(f'{base_url}/api/v1/health/db')
                validator.check('api', 'Database Health', r.status_code == 200,
                                f'HTTP {r.status_code}')
            except Exception as e:
                validator.check('api', 'Database Health', False, str(e))
    except ImportError:
        validator.check('api', 'Dependencies', False, 'httpx not installed')
    except Exception as e:
        validator.check('api', 'Connection', False, str(e))

    # --- Celery Check ---
    print("\n🌿 Celery")
    try:
        # Try to import but don't fail if broker is unreachable
        from app.celery import celery_app
        validator.check('celery', 'Celery Module', True, 'Imported')
    except Exception as e:
        validator.check('celery', 'Celery Module', False, str(e))

    # --- Security Check ---
    print("\n🔒 Security")
    required_env = [
        'JWT_SECRET', 'ENCRYPTION_KEY', 'DB_PASSWORD', 'REDIS_PASSWORD'
    ]
    for env in required_env:
        val = os.getenv(env, '')
        validator.check('security', f'{env} Set',
                        len(val) > 0 and val != 'changeme' and 'xxx' not in val.lower(),
                        'Set' if val else 'Not set',
                        {'length': len(val)})

    # --- Output Summary ---
    print("\n" + "=" * 70)
    summary = validator.summary()
    print(f"  Total Checks: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Pass Rate: {summary['pass_rate']}%")
    print("=" * 70)

    # Save report
    report = {
        'summary': summary,
        'checks': [r.to_dict() for r in validator.results],
    }
    with open('infra/validation_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to infra/validation_report.json")

    return summary['failed'] == 0


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)