# Database Optimization Features

This document describes the database optimization features implemented for the AI-F platform's PostgreSQL backend.

## Overview

The following optimizations have been implemented:

1. **Migration Rollback Testing** - Automated testing of Alembic migrations
2. **Point-in-Time Recovery (PITR)** - WAL archiving to S3 with recovery scripts
3. **Connection Pool Enhancement** - Health checks, monitoring, and failover
4. **Query Optimization** - Strategic indexes on frequently queried columns
5. **Database Monitoring** - Prometheus metrics with alerting
6. **Read Replica Failover** - Automatic health checking and failover
7. **Replication Testing** - Automated tests for replication consistency

---

## 1. Migration Rollback Testing

### Purpose
Ensure all Alembic migrations can be applied and reverted cleanly, maintaining data integrity.

### Implementation
- **File**: `backend/tests/integration/test_migrations.py`
- Tests upgrade all migrations from clean state
- Tests downgrade all migrations in reverse
- Tests full up/down cycle preserves data
- Uses separate test database: `face_recognition_test`

### Usage
```bash
# Run migration tests
pytest backend/tests/integration/test_migrations.py -v

# Set test database URL
export TEST_DATABASE_URL=postgresql://user:pass@localhost:5433/test_db
```

### CI Integration
Add to CI pipeline:
```yaml
- name: Test Database Migrations
  run: |
    docker-compose -f infra/docker-compose.yml up -d postgres
    sleep 10
    pytest backend/tests/integration/test_migrations.py -v
```

---

## 2. Point-in-Time Recovery (PITR)

### Architecture
Continuous WAL (Write-Ahead Log) archiving to S3 enables:
- Recovery to any point in time within retention window
- Full cluster restore from base backup + WAL replay
- Minimal RPO (Recovery Point Objective)

### Components

#### a) WAL Archiving Script
- **File**: `infra/docker-entrypoint-initdb.d/pg_basebackup.sh`
- Configures PostgreSQL `archive_command` to upload WAL segments to S3
- Creates initial base backup on deployment
- Sets up recovery configuration templates

#### b) Recovery Script
- **File**: Generated as `/var/lib/postgresql/data/pitr_recover.sh`
- Restores database to specific timestamp
- Downloads appropriate base backup
- Replays WAL segments up to target time

#### c) Documentation
- **File**: `docs/database/pitr_recovery_guide.md`

### Configuration

Set environment variables:
```bash
S3_BUCKET=postgres-wal-archive
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BACKUP_RETENTION_DAYS=7
```

### Recovery Procedures

#### Full Cluster Loss
```bash
# 1. Provision new instance
docker run -d --name pg-new ... postgres:15

# 2. Download latest base backup
aws s3 cp s3://$S3_BUCKET/base_backups/latest.tar.gz /tmp/
tar -xzf /tmp/latest.tar.gz -C /var/lib/postgresql/data/

# 3. Enable restore
echo "restore_command = 'aws s3 cp s3://$S3_BUCKET/wal_archive/%f %p'" >> postgresql.conf

# 4. Start - automatic WAL replay
pg_ctl start
```

#### Point-in-Time Recovery
```bash
./pitr_recover.sh "2026-05-08 12:00:00"
```

### RTO / RPO Targets
- **RTO** (Recovery Time Objective): 15-30 min (full restore), <30s (replica promotion)
- **RPO** (Recovery Point Objective): 5 min (configurable via `archive_timeout`)

---

## 3. Connection Pool Enhancements

### Pool Configuration

Updated pool parameters in `db_client.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_size` | 5 | Minimum connections kept open |
| `max_size` | 20 | Maximum connections allowed |
| `max_queries` | 50,000 | Recycle connection after N queries |
| `max_inactive_connection_lifetime` | 300s | Close connections idle > 5 min |

Configurable via environment variables:
```bash
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_POOL_MAX_QUERIES=50000
DB_POOL_MAX_INACTIVE_SECONDS=300
```

### Connection Health Checks

Each new connection runs `SELECT 1` validation and sets session parameters:
- `statement_timeout = 30s` - Prevent runaway queries
- `idle_in_transaction_session_timeout = 60s` - Auto-cancel idle transactions

### Failover Logic

Read replica failover with health checking:

```python
# Automatic health checks on connection checkout
# Falls back to primary if all replicas unhealthy
pool = await db._get_read_pool()
```

### Monitoring Integration

The `DatabaseMonitor` class tracks:
- Active/idle connections per pool
- Pool utilization percentage
- Replica health status
- Alerts on pool exhaustion (>90%)

### Usage
```python
from app.db.db_client import DBClient

db = DBClient()
await db.init_db()

# Check health
await db.health_check_replicas()

# Graceful shutdown
await db.close()
```

---

## 4. Query Optimization

### Indexes Added

Migration: `backend/alembic/versions/20260508_add_performance_indexes.py`

#### Recognition Pipeline
```sql
-- Embeddings
CREATE INDEX idx_embeddings_person_id ON embeddings(person_id);
CREATE INDEX idx_embeddings_camera_id ON embeddings(camera_id);

-- Persons
CREATE INDEX idx_persons_person_id ON persons(person_id);
CREATE INDEX idx_persons_org_id ON persons(org_id);
CREATE INDEX idx_persons_org_created ON persons(org_id, created_at DESC);
CREATE INDEX idx_persons_active ON persons(org_id) WHERE deleted_at IS NULL;
```

#### SaaS Operations
```sql
-- Users
CREATE INDEX idx_users_email ON users(email);

-- Subscriptions
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at) WHERE status = 'active';
```

#### Analytics & Timeline
```sql
-- Recognition events (most critical)
CREATE INDEX idx_recognition_events_camera ON recognition_events(camera_id, timestamp DESC);
CREATE INDEX idx_recognition_events_person ON recognition_events(person_id, timestamp DESC);
CREATE INDEX idx_recognition_events_org_camera_time ON recognition_events(org_id, camera_id, timestamp DESC);
CREATE INDEX idx_recognition_events_confidence ON recognition_events(confidence_score);
```

#### Compliance
```sql
-- Audit log
CREATE INDEX idx_audit_log_person_id ON audit_log(person_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_action_time ON audit_log(action, timestamp DESC);
```

#### Additional
- Model versions: `idx_model_versions_name_version`, `idx_model_versions_status`
- Support tickets: `idx_support_tickets_user`, `idx_support_tickets_status`
- Enrichment: `idx_enrichment_results_expires` (TTL cleanup)

### Partial Indexes

For active records only:
```sql
CREATE INDEX idx_persons_active ON persons(org_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at) WHERE status = 'active';
CREATE INDEX idx_enrichment_results_expires ON enrichment_results(expires_at) WHERE expires_at IS NOT NULL;
```

### pg_stat_statements Extension

Enabled in `_create_tables()` for query performance analysis:
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

View top slow queries:
```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## 5. Database Monitoring

### Module: `backend/app/monitoring/db_monitor.py`

The `DatabaseMonitor` class provides:

#### Prometheus Metrics Exported

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_connections_active` | Gauge | host, database | Active connections count |
| `db_connections_idle` | Gauge | host, database | Idle connections count |
| `db_connections_waiting` | Gauge | host, database | Waiting connection requests |
| `db_queries_total` | Counter | query_type, host, database | Total queries executed |
| `db_queries_duration_seconds` | Histogram | query_type, host, database | Query latency distribution |
| `db_slow_queries` | Counter | query_type, host, database | Slow queries exceeding threshold |
| `db_replication_lag_seconds` | Gauge | replica_name | Replication lag in seconds |
| `db_pool_utilization_percent` | Gauge | pool_name | Connection pool utilization |
| `db_transactions_total` | Counter | operation, host, database | Transaction count (begin/commit/rollback) |

#### Alerting

Alerts triggered when thresholds exceeded:
- **Pool exhaustion**: Utilization > 90%
- **Slow queries**: Single query > threshold (default 100ms)
- **Replication lag**: Lag > 5 seconds
- **Long-running queries**: Active > 30 seconds

Alert callbacks can be registered:
```python
from app.monitoring.db_monitor import get_monitor

def my_alert_handler(alert: Alert):
    print(f"ALERT: {alert.message}")

monitor = get_monitor()
monitor.register_alert_callback(my_alert_handler)
```

#### Query Performance Report

Generate performance insights:
```python
report = monitor.get_query_performance_report(last_minutes=10)
# Returns: avg/max times, slow query count, breakdown by query type
```

#### Background Monitoring

Automatic collection every 30 seconds (configurable):
- Collects connection pool stats
- Checks replication lag
- Monitors long-running queries
- Exposes metrics to `/metrics` endpoint

### Accessing Metrics

Already integrated with existing `/metrics` endpoint (from `app/metrics.py`):
```bash
curl http://localhost:8000/metrics | grep db_
```

### Configuration

Environment variables:
```bash
DB_SLOW_QUERY_THRESHOLD_MS=100
DB_POOL_EXHAUSTION_THRESHOLD_PCT=90
DB_REPLICATION_LAG_THRESHOLD_SEC=5
DB_MONITOR_INTERVAL_SECONDS=30
```

---

## 6. Read Replica Failover

### Enhancements to DBClient

#### Health Checking

Each replica connection validated with `SELECT 1` on checkout. Unhealthy replicas automatically skipped.

#### Failover Logic

```python
# Read queries automatically failover
result = await db.fetch("SELECT * FROM users", use_replica=True)
# Uses replica if healthy, otherwise falls back to primary
```

#### Configuration

```bash
# Environment variable for replica URLs
DB_READ_REPLICAS=replica1:5432,replica2:5432

# Or programmatically
db = DBClient(read_replicas=['replica1:5432', 'replica2:5432'])
```

#### Status Tracking

```python
# Check replica health
await db.health_check_replicas()
for health in db.read_replica_health:
    print(f"{health['url']}: {'healthy' if health['healthy'] else 'UNHEALTHY'}")
```

#### Round-Robin Load Balancing

Replicas used in round-robin fashion, with unhealthy replicas automatically removed from rotation.

### Replica Health Metrics

Exposed via Prometheus:
```
db_replication_lag_seconds{replica_name="replica1"} 0.5
db_connections_active{host="replica1"} 5
```

---

## 7. Replication Testing

### Test Suite

**File**: `backend/tests/integration/test_replication.py`

#### Test Cases

1. **test_write_propagates_to_replica**
   - Verifies write to primary appears on replica within 5 seconds SLA
   - Measures actual replication lag

2. **test_replica_health_checking**
   - Validates health check mechanism
   - Confirms replica marked healthy/unhealthy correctly

3. **test_read_queries_use_replicas**
   - Ensures `use_replica=True` routes to replica pool

4. **test_replica_failover_on_down**
   - Simulates replica failure
   - Verifies fallback to primary or other replicas

5. **test_round_robin_load_balancing**
   - Confirms round-robin distribution across replicas

6. **test_consistency_after_multiple_writes**
   - Batch writes and verifies consistency

7. **test_replication_with_complex_query**
   - Joins and aggregations across replica

8. **test_replication_lag_alerting**
   - Ensures lag thresholds monitored

### Running Tests

```bash
# Start primary + replica
cd infra
./setup_replication_test.sh

# Configure environment
export DB_HOST=localhost
export DB_PORT=5432
export DB_PASSWORD=generated_primary_password
export DB_READ_REPLICAS=localhost:5433
export DB_USER=postgres
export DB_NAME=face_recognition

# Run tests
cd ../backend
pytest tests/integration/test_replication.py -v -m integration
```

### Local Development Setup

The `infra/setup_replication_test.sh` script provisions a primary and replica PostgreSQL container pair with replication configured.

Requires:
- Docker
- `aws` CLI (for S3 operations, can skip for local test)
- `openssl` (for password generation)

---

## Environment Variables Reference

### Database Connection

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | Primary database host |
| `DB_PORT` | `5432` | Primary database port |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `password` | Database password |
| `DB_NAME` | `face_recognition` | Database name |
| `DB_READ_REPLICAS` | (empty) | Comma-separated replica URLs |

### Connection Pool

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_MIN_SIZE` | `5` | Minimum pool size |
| `DB_POOL_MAX_SIZE` | `20` | Maximum pool size |
| `DB_POOL_MAX_QUERIES` | `50000` | Recycle after N queries |
| `DB_POOL_MAX_INACTIVE_SECONDS` | `300` | Max idle time before recycle |

### Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_SLOW_QUERY_THRESHOLD_MS` | `100` | Slow query threshold |
| `DB_POOL_EXHAUSTION_THRESHOLD_PCT` | `90` | Alert when pool >90% full |
| `DB_REPLICATION_LAG_THRESHOLD_SEC` | `5` | Alert when replica lag >5s |
| `DB_MONITOR_INTERVAL_SECONDS` | `30` | Metrics collection interval |

### PITR

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_BUCKET` | - | S3 bucket for WAL archives |
| `S3_REGION` | `us-east-1` | AWS region |
| `S3_ENDPOINT` | (empty) | Custom S3 endpoint |
| `AWS_ACCESS_KEY_ID` | - | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | - | S3 secret key |
| `BACKUP_RETENTION_DAYS` | `7` | Retention period |

---

## Performance Tuning Recommendations

### Connection Pool

For high-traffic deployments (RPS > 1000):
```bash
DB_POOL_MIN_SIZE=20
DB_POOL_MAX_SIZE=50
```

### Indexes

Monitor index usage:
```sql
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

Drop unused indexes to reduce write overhead.

### Query Optimization

Use `EXPLAIN ANALYZE` on slow queries:
```sql
-- Enable pg_stat_statements
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%FROM embeddings%'
ORDER BY mean_exec_time DESC
LIMIT 5;
```

### Replication

For read-heavy workloads (80% reads):
- Deploy 2-3 read replicas
- Use connection pool size 5-10 per replica
- Configure load balancer in front of replicas

---

## Troubleshooting

### Migration Tests Fail

**Symptom**: `test_migrations.py` fails on specific revision

**Diagnosis**:
```bash
# Check migration order
alembic -c backend/alembic.ini history
```

**Fix**: Ensure `down_revision` and `revises` fields are correct in migration files.

### Replication Lag Too High

**Symptom**: `db_replication_lag_seconds` metric increasing

**Diagnosis**:
```sql
-- Check replica throughput
SELECT * FROM pg_stat_replication;

-- Check WAL sender status
SELECT * FROM pg_replication_slots;
```

**Fix**:
- Increase `max_wal_senders`
- Tune `wal_sender_timeout`
- Check network latency between primary/replica
- Consider using streaming replication vs. logical replication

### Pool Exhaustion Alerts

**Symptom**: `db_pool_utilization_percent` > 90%

**Diagnosis**:
```sql
-- Check for idle in transaction connections
SELECT pid, state, query_start, query 
FROM pg_stat_activity 
WHERE state = 'idle in transaction';
```

**Fix**:
- Increase pool max_size
- Ensure connections are properly closed (use context managers)
- Check for long-running transactions

### Slow Queries

**Diagnosis**:
```sql
-- Identify top slow queries
SELECT query, mean_exec_time, calls, rows 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check if indexes used
EXPLAIN (ANALYZE, BUFFERS) <slow_query>;
```

**Fix**: Add missing indexes or rewrite query.

---

## Metrics Reference

All metrics available at `GET /metrics`:

```
# HELP db_connections_active Number of active database connections
# TYPE db_connections_active gauge
db_connections_active{host="localhost",database="face_recognition"} 12.0

# HELP db_queries_total Total number of database queries
# TYPE db_queries_total counter
db_queries_total{query_type="SELECT",host="localhost",database="face_recognition"} 15243.0

# HELP db_queries_duration_seconds Database query duration
# TYPE db_queries_duration_seconds histogram
db_queries_duration_seconds_bucket{query_type="SELECT",le="0.005"} 1200.0
...
```

---

## Further Reading

- PostgreSQL Performance Optimization: https://wiki.postgresql.org/wiki/Performance_Optimization
- pgvector performance: https://github.com/pgvector/pgvector#performance
- Alembic migrations: https://alembic.sqlalchemy.org/en/latest/
- Prometheus client Python: https://github.com/prometheus/client_python
