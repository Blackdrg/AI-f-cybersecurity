# Database Optimization Agent Instructions

This document provides instructions for running and maintaining the database optimization features implemented in this repository.

**Status: ✅ PRODUCTION READY (v2.2.1)**

---

## Quick Reference

### Run Migration Tests
```bash
cd backend
pytest tests/integration/test_migrations.py -v
```

### Run Replication Tests
```bash
# First start test environment
cd infra
./setup_replication_test.sh

# Configure DB env vars (script outputs these)
export DB_HOST=localhost
export DB_PORT=5432
export DB_READ_REPLICAS=localhost:5433
export DB_USER=postgres
export DB_PASSWORD=<from script output>
export DB_NAME=face_recognition

# Run tests
cd ../backend
pytest tests/integration/test_replication.py -v
```

### View Database Metrics
```bash
curl http://localhost:8000/metrics | grep db_
```

### Apply Performance Indexes Migration
```bash
cd backend
alembic -c alembic.ini upgrade head
```

### Check Replication Lag
```sql
SELECT 
    application_name,
    pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn) as lag_bytes,
    (pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn) / 16 / 1024) as lag_seconds
FROM pg_stat_replication
WHERE state = 'streaming';
```

### Perform PITR Recovery
```bash
# On database host
/var/lib/postgresql/data/pitr_recover.sh "2026-05-08 12:00:00"
```

---

## Feature Overview

1. **Migration Rollback Testing** (`tests/integration/test_migrations.py`)
   - Tests all Alembic migrations can upgrade/downgrade
   - Uses isolated test database
   - Verifies data integrity

2. **Point-in-Time Recovery** (`infra/docker-entrypoint-initdb.d/pg_basebackup.sh`)
   - WAL archiving to S3
   - Base backup creation
   - Recovery scripts
   - Documentation: `docs/database/pitr_recovery_guide.md`

3. **Connection Pool Tuning** (`backend/app/db/db_client.py`)
   - Health checks on connection checkout (`SELECT 1`)
   - Configurable pool sizes via env vars
   - Connection recycling
   - Stale connection handling

4. **Query Optimization** (`backend/alembic/versions/20260508_add_performance_indexes.py`)
   - Indexes on `person_id`, `user_id`, `camera_id`, `created_at`
   - Partial indexes for active records
   - Composite indexes for common queries
   - `pg_stat_statements` extension enabled

5. **Database Monitoring** (`backend/app/monitoring/db_monitor.py`)
   - Prometheus metrics: `db_connections_*`, `db_queries_*`, `db_replication_lag_seconds`
   - Alerts on pool exhaustion, slow queries, replication lag
   - Background monitoring task
   - Query performance reports

6. **Replica Failover** (`backend/app/db/db_client.py` updates)
   - Health checking per replica
   - Round-robin with automatic exclusion of unhealthy replicas
   - `health_check_replicas()` method

7. **Replication Testing** (`backend/tests/integration/test_replication.py`)
   - Write propagation tests (< 5s SLA)
   - Failover scenarios
   - Consistency verification

---

## Troubleshooting Tips

### Migration Tests Fail with "table already exists"
```bash
# Clean test database
dropdb -U postgres face_recognition_test
createdb -U postgres face_recognition_test
```

### Replication Tests Timeout
```bash
# Check replica health
docker logs pg-replica
docker exec pg-primary psql -c "SELECT * FROM pg_stat_replication;"
```

### High Pool Utilization
Check for leaked connections:
```sql
SELECT pid, state, query, now() - query_start as duration
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

### No Metrics Exported
```bash
# Verify db_monitor initialized
curl http://localhost:8000/metrics | grep db_connections_active
# Should return metric line
```

---

## Configuration Checklist

- [ ] Set `DB_POOL_MAX_SIZE` based on RPS requirements
- [ ] Configure `DB_READ_REPLICAS` for read scaling
- [ ] Enable `DB_SLOW_QUERY_THRESHOLD_MS` monitoring
- [ ] Set up S3 bucket for PITR if needed
- [ ] Schedule weekly recovery tests
- [ ] Monitor `db_replication_lag_seconds` in dashboard
- [ ] Review slow query logs periodically
- [ ] Set up alerts for pool exhaustion

---

## Related Files

```
backend/app/db/db_client.py - Connection pool + failover
backend/app/monitoring/db_monitor.py - Metrics + alerts
backend/tests/integration/test_migrations.py - Migration tests
backend/tests/integration/test_replication.py - Replication tests
backend/alembic/versions/20260508_add_performance_indexes.py - Index migration
infra/docker-entrypoint-initdb.d/pg_basebackup.sh - PITR setup
docs/database/pitr_recovery_guide.md - PITR docs
docs/database/optimization_guide.md - Feature guide
```

---

## Prometheus Alerts (suggested)

```yaml
- alert: HighDBConnectionPoolUtilization
  expr: db_pool_utilization_percent > 90
  for: 2m
  annotations:
    summary: "DB connection pool utilization high"

- alert: HighReplicationLag
  expr: db_replication_lag_seconds > 5
  for: 1m
  annotations:
    summary: "Replication lag exceeds 5 seconds"

- alert: SlowQueryRate
  expr: rate(db_slow_queries[1m]) > 10
  annotations:
    summary: "More than 10 slow queries per second"
```

---

## Version History

- **2026-05-08**: Initial implementation of all 7 features
