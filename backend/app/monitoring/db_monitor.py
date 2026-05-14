"""
Database Monitoring and Observability Module
- Prometheus metrics for PostgreSQL, Redis, Celery
- Alert thresholds with configurable callbacks
- Replication lag monitoring
- Slow query detection
- Background monitoring task
"""
import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import os

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, generate_latest, REGISTRY,
        Summary, Info
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents a monitoring alert."""
    severity: AlertSeverity
    metric_name: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryMetrics:
    """Metrics for an individual query."""
    query: str
    execution_time_ms: float
    rows_returned: int
    timestamp: datetime
    query_type: str = 'SELECT'


class DatabaseMonitor:
    """Comprehensive database monitoring with Prometheus export."""

    def __init__(self, db_client=None):
        """Initialize database monitor with Prometheus metrics."""
        self.db_client = db_client
        self._alerts: List[Alert] = []
        self._query_history: List[QueryMetrics] = []
        self._max_query_history = 2000
        self._running = False

        if not PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_client not available, monitoring disabled")
            return

        # ============================================================
        # PROMETHEUS METRICS DEFINITIONS
        # ============================================================

        # --- Connection Pool Metrics ---
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Number of active database connections',
            ['host', 'database', 'pool']
        )
        self.db_connections_idle = Gauge(
            'db_connections_idle',
            'Number of idle database connections',
            ['host', 'database', 'pool']
        )
        self.db_connections_waiting = Gauge(
            'db_connections_waiting',
            'Number of connections waiting for a pool slot',
            ['host', 'database']
        )
        self.db_pool_size = Gauge(
            'db_pool_size',
            'Maximum pool size configured',
            ['host', 'database', 'pool']
        )

        # --- Query Metrics ---
        self.db_queries_total = Counter(
            'db_queries_total',
            'Total number of database queries executed',
            ['query_type', 'host', 'database']
        )
        self.db_queries_duration_seconds = Histogram(
            'db_queries_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'host', 'database'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1,
                     0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        self.db_slow_queries = Counter(
            'db_slow_queries_total',
            'Number of slow queries exceeding threshold',
            ['query_type', 'host', 'database']
        )

        # --- Replication Metrics ---
        self.db_replication_lag_seconds = Gauge(
            'db_replication_lag_seconds',
            'Replication lag in seconds',
            ['replica_name']
        )
        self.db_replication_status = Gauge(
            'db_replication_status',
            'Replication status (1=streaming, 0=disconnected)',
            ['replica_name', 'state']
        )

        # --- Pool Utilization ---
        self.db_pool_utilization = Gauge(
            'db_pool_utilization_percent',
            'Connection pool utilization percentage',
            ['pool_name']
        )

        # --- Transaction Metrics ---
        self.db_transactions_total = Counter(
            'db_transactions_total',
            'Total database transactions',
            ['operation', 'host', 'database']
        )

        # --- System Health Metrics ---
        self.db_table_rows = Gauge(
            'db_table_rows_count',
            'Approximate number of rows per table',
            ['table_name']
        )
        self.db_index_usage = Gauge(
            'db_index_usage_ratio',
            'Index usage ratio (index scans / total scans)',
            ['index_name', 'table_name']
        )

        # --- Redis Metrics ---
        self.redis_connected_clients = Gauge(
            'redis_connected_clients',
            'Number of connected Redis clients'
        )
        self.redis_memory_used_bytes = Gauge(
            'redis_memory_used_bytes',
            'Redis memory usage in bytes'
        )
        self.redis_commands_total = Counter(
            'redis_commands_total',
            'Total Redis commands executed',
            ['command']
        )
        self.redis_hit_rate = Gauge(
            'redis_cache_hit_rate_percent',
            'Redis cache hit rate percentage'
        )

        # --- Celery Metrics ---
        self.celery_tasks_total = Counter(
            'celery_tasks_total',
            'Total Celery tasks processed',
            ['task_name', 'queue', 'status']
        )
        self.celery_task_duration_seconds = Histogram(
            'celery_task_duration_seconds',
            'Celery task execution duration',
            ['task_name', 'queue'],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
        )
        self.celery_queue_length = Gauge(
            'celery_queue_length',
            'Number of pending tasks in queue',
            ['queue']
        )
        self.celery_workers_online = Gauge(
            'celery_workers_online',
            'Number of online Celery workers'
        )

        # --- HTTP/API Metrics ---
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'path', 'status']
        )
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'path'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )

        # --- Recognition-specific Metrics ---
        self.recognition_latency = Histogram(
            'recognition_latency_seconds',
            'Face recognition pipeline latency',
            ['mode', 'camera_id'],
            buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0)
        )
        self.enrollment_rate = Counter(
            'enrollments_total',
            'Total enrollment operations',
            ['status']
        )

        # --- Alert Counters ---
        self.alerts_generated_total = Counter(
            'alerts_generated_total',
            'Total alerts generated',
            ['severity', 'type']
        )

        # Thresholds (configurable via env vars)
        self.slow_query_threshold_ms = float(
            os.environ.get('DB_SLOW_QUERY_THRESHOLD_MS', '100')
        )
        self.pool_exhaustion_threshold_pct = float(
            os.environ.get('DB_POOL_EXHAUSTION_THRESHOLD_PCT', '90')
        )
        self.replication_lag_threshold_sec = float(
            os.environ.get('DB_REPLICATION_LAG_THRESHOLD_SEC', '5')
        )
        self.monitoring_interval = int(
            os.environ.get('DB_MONITOR_INTERVAL_SECONDS', '30')
        )

        # Alert callbacks
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None

    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """Register a callback to be invoked when an alert is generated."""
        self.alert_callbacks.append(callback)

    async def start_background_monitoring(self):
        """Start background monitoring task."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._running = True
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
            logger.info("Background database monitoring started")

    async def stop_background_monitoring(self):
        """Stop background monitoring task."""
        self._running = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Background database monitoring stopped")

    async def _monitor_loop(self):
        """Background monitoring loop with error recovery."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self._running:
            try:
                await self.collect_metrics()
                await self.check_thresholds()
                consecutive_errors = 0
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Monitoring loop error ({consecutive_errors}/{max_consecutive_errors}): {e}",
                             exc_info=True)
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical("Too many consecutive errors, backing off...")
                    await asyncio.sleep(self.monitoring_interval * 5)
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(self.monitoring_interval)

    async def collect_metrics(self):
        """Collect current database and system metrics."""
        host = os.environ.get('DB_HOST', 'localhost')
        database = os.environ.get('DB_NAME', 'face_recognition')

        if self.db_client and self.db_client.pool:
            pool = self.db_client.pool
            try:
                # Pool metrics via asyncpg
                if hasattr(pool, '_minsize') and hasattr(pool, '_maxsize'):
                    min_size = pool._minsize
                    max_size = pool._maxsize
                    used = getattr(pool, '_usedcount', 0)
                    reserved = getattr(pool, '_reservesize', 0)

                    self.db_pool_size.labels(host=host, database=database, pool='primary').set(max_size)
                    self.db_connections_active.labels(host=host, database=database, pool='primary').set(used)
                    self.db_connections_idle.labels(host=host, database=database, pool='primary').set(
                        max(0, max_size - used - reserved))

                    if max_size > 0:
                        utilization = (used / max_size) * 100
                        self.db_pool_utilization.labels(pool_name='primary').set(utilization)

                # Database-level queries
                async with pool.acquire() as conn:
                    # Active/idle connections
                    active_conn = await conn.fetchval(
                        "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
                    )
                    idle_conn = await conn.fetchval(
                        "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'idle'"
                    )

                    self.db_connections_active.labels(
                        host=host, database=database, pool='pg_stat'
                    ).set(active_conn or 0)
                    self.db_connections_idle.labels(
                        host=host, database=database, pool='pg_stat'
                    ).set(idle_conn or 0)

                    # Replication lag
                    await self._check_replication_lag(conn)

                    # Table row counts (sampled)
                    await self._collect_table_stats(conn)

                    # PG Stat statements
                    await self._collect_pg_stat_statements(conn)

            except Exception as e:
                logger.error(f"Failed to collect DB metrics: {e}", exc_info=True)

        # Collect Redis metrics if available
        await self._collect_redis_metrics()

    async def _check_replication_lag(self, conn):
        """Check replication lag for read replicas."""
        try:
            result = await conn.fetch("""
                SELECT
                    application_name,
                    client_addr,
                    pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn) as lag_bytes,
                    COALESCE(
                        EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::float,
                        0
                    ) as lag_seconds,
                    state,
                    sent_lsn,
                    replay_lsn
                FROM pg_stat_replication
                WHERE state = 'streaming'
            """)

            for row in result:
                lag_seconds = row['lag_seconds'] or 0
                replica_name = row['application_name'] or row['client_addr'] or 'replica'

                self.db_replication_lag_seconds.labels(replica_name=str(replica_name)).set(lag_seconds)
                self.db_replication_status.labels(
                    replica_name=str(replica_name), state='streaming'
                ).set(1)

                if lag_seconds > self.replication_lag_threshold_sec:
                    alert = Alert(
                        severity=AlertSeverity.WARNING,
                        metric_name='replication_lag',
                        message=f"Replication lag on {replica_name}: {lag_seconds:.1f}s (threshold: {self.replication_lag_threshold_sec}s)",
                        context={
                            'replica': replica_name,
                            'lag_seconds': lag_seconds,
                            'threshold': self.replication_lag_threshold_sec
                        }
                    )
                    self._trigger_alert(alert)

        except Exception as e:
            logger.debug(f"Replication check skipped: {e}")

    async def _collect_pg_stat_statements(self, conn):
        """Collect query statistics from pg_stat_statements."""
        try:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
            )
            if not exists:
                return

            stmt_stats = await conn.fetch("""
                SELECT
                    queryid,
                    left(query, 100) as query_preview,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time,
                    rows
                FROM pg_stat_statements
                ORDER BY total_exec_time DESC
                LIMIT 20
            """)

            for stmt in stmt_stats:
                if stmt['calls'] and stmt['mean_exec_time'] > self.slow_query_threshold_ms:
                    self.db_slow_queries.labels(
                        query_type='STATEMENT', host='localhost', database='face_recognition'
                    ).inc(stmt['calls'])

        except Exception as e:
            logger.debug(f"pg_stat_statements collection failed: {e}")

    async def _collect_table_stats(self, conn):
        """Collect approximate row counts for key tables."""
        try:
            key_tables = [
                'persons', 'embeddings', 'recognition_events', 'alerts',
                'users', 'cameras', 'api_keys', 'subscriptions',
                'audit_log', 'system_health', 'system_celery_tasks',
                'notifications_outbox'
            ]
            for table in key_tables:
                try:
                    count = await conn.fetchval(f"""
                        SELECT reltuples::bigint FROM pg_class
                        WHERE relname = '{table}'
                    """)
                    if count is not None:
                        self.db_table_rows.labels(table_name=table).set(count)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Table stats collection failed: {e}")

    async def _collect_redis_metrics(self):
        """Collect Redis metrics if accessible."""
        try:
            import redis.asyncio as redis
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url, decode_responses=True)

            info = await r.info()
            self.redis_memory_used_bytes.set(info.get('used_memory', 0))
            self.redis_connected_clients.set(info.get('connected_clients', 0))

            # Hit rate calculation
            stats = info.get('stats', {})
            hits = stats.get('keyspace_hits', 0)
            misses = stats.get('keyspace_misses', 0)
            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                self.redis_hit_rate.set(hit_rate)

            await r.close()
        except Exception:
            pass

    def track_query(self, query: str, execution_time_ms: float,
                    rows_returned: int, query_type: str = 'SELECT'):
        """Track a query execution for metrics."""
        host = os.environ.get('DB_HOST', 'localhost')
        database = os.environ.get('DB_NAME', 'face_recognition')

        # Record history
        qm = QueryMetrics(
            query=query.strip()[:200],
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            timestamp=datetime.utcnow(),
            query_type=query_type
        )
        self._query_history.append(qm)
        if len(self._query_history) > self._max_query_history:
            self._query_history = self._query_history[-self._max_query_history:]

        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            self.db_queries_total.labels(
                query_type=query_type, host=host, database=database
            ).inc()
            self.db_queries_duration_seconds.labels(
                query_type=query_type, host=host, database=database
            ).observe(execution_time_ms / 1000.0)

            if execution_time_ms > self.slow_query_threshold_ms:
                self.db_slow_queries.labels(
                    query_type=query_type, host=host, database=database
                ).inc()

                alert = Alert(
                    severity=AlertSeverity.WARNING,
                    metric_name='slow_query',
                    message=f"Slow query: {query[:100]} took {execution_time_ms:.1f}ms",
                    context={
                        'query': query[:500],
                        'execution_time_ms': execution_time_ms,
                        'threshold_ms': self.slow_query_threshold_ms,
                        'rows_returned': rows_returned
                    }
                )
                self._trigger_alert(alert)

    async def check_thresholds(self):
        """Check all monitoring thresholds and generate alerts."""
        host = os.environ.get('DB_HOST', 'localhost')

        # Check pool exhaustion
        if self.db_client and self.db_client.pool:
            pool = self.db_client.pool
            try:
                if hasattr(pool, '_maxsize') and hasattr(pool, '_usedcount'):
                    max_size = pool._maxsize
                    used = pool._usedcount
                    if max_size > 0 and used > 0:
                        utilization_pct = (used / max_size) * 100
                        if utilization_pct >= self.pool_exhaustion_threshold_pct:
                            alert = Alert(
                                severity=AlertSeverity.CRITICAL,
                                metric_name='pool_exhaustion',
                                message=f"Pool {utilization_pct:.1f}% full ({used}/{max_size})",
                                context={
                                    'pool': 'primary',
                                    'active': used,
                                    'max': max_size,
                                    'utilization_pct': utilization_pct
                                }
                            )
                            self._trigger_alert(alert)

                # Check long-running queries
                async with pool.acquire() as conn:
                    long_queries = await conn.fetch("""
                        SELECT pid, query, state,
                               now() - query_start AS duration,
                               pg_stat_activity.query_start
                        FROM pg_stat_activity
                        WHERE state = 'active'
                          AND query_start IS NOT NULL
                          AND now() - query_start > interval '30 seconds'
                          AND pid <> pg_backend_pid()
                        LIMIT 20
                    """)
                    for row in long_queries:
                        alert = Alert(
                            severity=AlertSeverity.WARNING,
                            metric_name='long_running_query',
                            message=f"Long query ({row['duration']}): {row['query'][:100]}",
                            context={
                                'pid': row['pid'],
                                'duration': str(row['duration']),
                                'query': row['query'][:500]
                            }
                        )
                        self._trigger_alert(alert)
            except Exception as e:
                logger.error(f"Threshold check error: {e}", exc_info=True)

    def _trigger_alert(self, alert: Alert):
        """Trigger an alert and invoke all callbacks."""
        self._alerts.append(alert)
        level = logging.WARNING if alert.severity == AlertSeverity.WARNING else logging.CRITICAL
        logger.log(level, f"ALERT [{alert.severity.value.upper()}] {alert.message}")

        # Keep only recent alerts
        if len(self._alerts) > 10000:
            self._alerts = self._alerts[-5000:]

        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def get_recent_alerts(self, since: Optional[datetime] = None) -> List[Alert]:
        """Get recent alerts, optionally filtered by time."""
        if since:
            return [a for a in self._alerts if a.timestamp >= since]
        return self._alerts.copy()

    def get_prometheus_metrics(self) -> bytes:
        """Export Prometheus metrics in text format."""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(REGISTRY)
        return b"# Metrics disabled"

    def get_query_performance_report(self, last_minutes: int = 10) -> Dict[str, Any]:
        """Generate query performance report."""
        cutoff = datetime.utcnow() - timedelta(minutes=last_minutes)
        recent = [q for q in self._query_history if q.timestamp >= cutoff]

        if not recent:
            return {"message": "No queries in time window"}

        total = len(recent)
        avg_time = sum(q.execution_time_ms for q in recent) / total
        max_time = max(q.execution_time_ms for q in recent)
        slow = [q for q in recent if q.execution_time_ms > self.slow_query_threshold_ms]

        query_types: Dict[str, List[float]] = {}
        for q in recent:
            qtype = q.query.split()[0] if q.query.split() else 'UNKNOWN'
            query_types.setdefault(qtype, []).append(q.execution_time_ms)

        type_stats = {
            qt: {
                'count': len(times),
                'avg_ms': sum(times) / len(times),
                'max_ms': max(times)
            }
            for qt, times in query_types.items()
        }

        return {
            'time_window_minutes': last_minutes,
            'total_queries': total,
            'avg_execution_time_ms': avg_time,
            'max_execution_time_ms': max_time,
            'slow_queries_count': len(slow),
            'slow_query_threshold_ms': self.slow_query_threshold_ms,
            'query_type_breakdown': type_stats,
            'slowest_queries': sorted(
                recent, key=lambda q: q.execution_time_ms, reverse=True
            )[:10]
        }


# Global monitor instance
_monitor: Optional[DatabaseMonitor] = None


def get_monitor() -> DatabaseMonitor:
    """Get or create global database monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = DatabaseMonitor()
    return _monitor


def init_monitor(db_client=None) -> DatabaseMonitor:
    """Initialize global monitor with DB client."""
    global _monitor
    _monitor = DatabaseMonitor(db_client)
    return _monitor