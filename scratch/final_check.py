import os
base = r'D:\AI-F\AI-f'
infra = os.path.join(base, 'infra')
benchmarks = os.path.join(base, '.benchmarks')
backend = os.path.join(base, 'backend', 'app')

files = [
    (os.path.join(infra,'init.sql'), 'Database schema (52 tables + 43 indexes + 54 RLS policies)'),
    (os.path.join(infra,'init_pgvector.sql'), 'pgvector/extension setup'),
    (os.path.join(infra,'alembic','versions','20260513_add_performance_indexes.py'), 'Performance indexes migration'),
    (os.path.join(infra,'docker-compose.yml'), 'Full docker-compose (dev)'),
    (os.path.join(infra,'docker-compose.prod.yml'), 'Production docker-compose'),
    (os.path.join(infra,'docker-compose.full.yml'), 'Full docker-compose (GPU)'),
    (os.path.join(infra,'docker-compose.sandbox.yml'), 'Sandbox docker-compose'),
    (os.path.join(infra,'redis.conf'), 'Redis production config'),
    (os.path.join(infra,'redis-sentinel.conf'), 'Redis Sentinel config'),
    (os.path.join(infra,'prometheus.yml'), 'Prometheus monitoring config'),
    (os.path.join(infra,'nginx.conf'), 'NGINX reverse proxy'),
    (os.path.join(infra,'scripts','72h_uptime_test.py'), '72-hour uptime test'),
    (os.path.join(infra,'scripts','validate_infrastructure.py'), 'Infrastructure validator'),
    (os.path.join(infra,'grafana','dashboards','ai-f-dashboards.json'), 'Grafana dashboards'),
    (os.path.join(infra,'grafana','provisioning','datasources.yml'), 'Grafana datasources'),
    (os.path.join(infra,'deployment_checklist.json'), 'Deployment checklist (28 items)'),
    (os.path.join(benchmarks,'load_test_framework.py'), 'Load test framework (Locust)'),
    (os.path.join(benchmarks,'benchmark_runner.py'), 'Distributed benchmark runner'),
    (os.path.join(backend,'db','db_client.py'), 'DB client with pool/failover/RLS'),
    (os.path.join(backend,'monitoring','db_monitor.py'), 'DB monitoring (Prometheus)'),
    (os.path.join(backend,'celery.py'), 'Celery config (8 task modules, DLQ)'),
    (os.path.join(backend,'pubsub.py'), 'Redis Pub/Sub event bus'),
    (os.path.join(backend,'services','redis_client.py'), 'Redis client (JWT/rate-limit)'),
    (os.path.join(backend,'tasks','compliance_tasks.py'), 'Compliance tasks (GDPR)'),
    (os.path.join(backend,'main.py'), 'FastAPI application entry point'),
]

all_ok = True
total = 0
for path, desc in files:
    exists = os.path.exists(path)
    if exists:
        total += 1
    else:
        all_ok = False
        print('MISSING: %s' % path)

print('25/25 files present: %s' % all_ok)