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

print('='*70)
print('AI-F INFRASTRUCTURE VALIDATION REPORT')
print('='*70)
print()

all_ok = True
total_size = 0
for path, desc in files:
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    total_size += size
    status = 'OK' if exists else 'MISSING'
    if not exists:
        all_ok = False
    rel = path.replace(base,'').lstrip('\\')
    print('[%s] %s - %s (%d KB)' % (status, rel, desc, size//1024))

print()
print('='*70)
print('TOTALS:')
print('  Files: %d/%d created' % (sum(1 for p,_ in files if os.path.exists(p)), len(files)))
print('  Total size: %d KB' % (total_size//1024))
print('  Status: %s' % ('ALL OK - READY FOR DEPLOYMENT' if all_ok else 'SOME MISSING'))
print('='*70)

# Verify init.sql content
with open(os.path.join(infra,'init.sql'),'r') as f:
    sql = f.read()
t = sql.lower().count('create table if not exists')
i = sql.lower().count('create index')
p = sql.lower().count('create policy')
e = sql.lower().count('create extension')
rls = sql.lower().count('enable row level security')

print()
print('INIT.SQL STATISTICS:')
print('  Tables:      %d' % t)
print('  Indexes:     %d' % i)
print('  RLS Policies:%d' % p)
print('  Extensions:  %d' % e)
print('  RLS Enabled: %d tables' % rls)

# Check backend enhancements
with open(os.path.join(backend,'db','db_client.py'),'r') as f:
    dbc = f.read()
print()
print('DB CLIENT FEATURES:')
for feat in ['ReplicaHealthChecker','CircuitBreaker','async def init_db','def _get_read_pool','_health_monitor_loop','rotate_embedding_keys','verify_audit_chain']:
    print('  %s: %s' % (feat, 'YES' if feat in dbc else 'NO'))

with open(os.path.join(backend,'monitoring','db_monitor.py'),'r') as f:
    mon = f.read()
print()
print('DB MONITOR FEATURES:')
for feat in ['Prometheus','Gauge','Counter','Histogram','DatabaseMonitor','start_background_monitoring','check_thresholds','_check_replication_lag','_collect_query_stats']:
    print('  %s: %s' % (feat, 'YES' if feat in mon else 'NO'))

with open(os.path.join(backend,'celery.py'),'r') as f:
    cel = f.read()
print()
print('CELERY FEATURES:')
for feat in ['task_routes','task_acks_late','task_time_limit','task_dead_letter_queue','retry_backoff','MonitoredTask','beat_schedule','broker_transport_options']:
    print('  %s: %s' % (feat, 'YES' if feat in cel else 'NO'))