"""Database monitoring and observability module.

This module provides comprehensive monitoring for PostgreSQL including:
- Connection pool metrics
- Query latency tracking
- Slow query detection
- Replication lag monitoring
- Alert generation for threshold breaches
- Prometheus metrics export
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import os

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

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
    parameters: Optional[tuple] = None


class DatabaseMonitor:
    """Comprehensive database monitoring with Prometheus export."""
    
    def __init__(self, db_client=None):
        """Initialize database monitor with Prometheus metrics."""
        self.db_client = db_client
        self._alerts: List[Alert] = []
        self._query_history: List[QueryMetrics] = []
        self._max_query_history = 1000
        
        # Prometheus metrics
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Number of active database connections',
            ['host', 'database']
        )
        
        self.db_connections_idle = Gauge(
            'db_connections_idle',
            'Number of idle database connections',
            ['host', 'database']
        )
        
        self.db_connections_waiting = Gauge(
            'db_connections_waiting',
            'Number of connections waiting for a pool slot',
            ['host', 'database']
        )
        
        self.db_queries_total = Counter(
            'db_queries_total',
            'Total number of database queries',
            ['query_type', 'host', 'database']
        )
        
        self.db_queries_duration_seconds = Histogram(
            'db_queries_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'host', 'database'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        self.db_slow_queries = Counter(
            'db_slow_queries',
            'Number of slow queries exceeding threshold',
            ['query_type', 'host', 'database']
        )
        
        self.db_replication_lag_seconds = Gauge(
            'db_replication_lag_seconds',
            'Replication lag in seconds',
            ['replica_name']
        )
        
        self.db_pool_utilization = Gauge(
            'db_pool_utilization_percent',
            'Connection pool utilization percentage',
            ['pool_name']
        )
        
        self.db_transactions_total = Counter(
            'db_transactions_total',
            'Total database transactions',
            ['operation'],  # 'begin', 'commit', 'rollback'
            ['host', 'database']
        )
        
        # Slow query threshold (ms)
        self.slow_query_threshold_ms = float(
            os.environ.get('DB_SLOW_QUERY_THRESHOLD_MS', '100')
        )
        
        # Pool exhaustion threshold (%)
        self.pool_exhaustion_threshold_pct = float(
            os.environ.get('DB_POOL_EXHAUSTION_THRESHOLD_PCT', '90')
        )
        
        # Replication lag threshold (seconds)
        self.replication_lag_threshold_sec = float(
            os.environ.get('DB_REPLICATION_LAG_THRESHOLD_SEC', '5')
        )
        
        # Alert callback
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Background monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = int(
            os.environ.get('DB_MONITOR_INTERVAL_SECONDS', '30')
        )
        
        logger.info("DatabaseMonitor initialized")
    
    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """Register a callback to be invoked when an alert is generated."""
        self.alert_callbacks.append(callback)
    
    async def start_background_monitoring(self):
        """Start background monitoring task."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
            logger.info("Background database monitoring started")
    
    async def stop_background_monitoring(self):
        """Stop background monitoring task."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Background database monitoring stopped")
    
    async def _monitor_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await self.collect_metrics()
                await self.check_thresholds()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self._monitoring_interval)
    
    async def collect_metrics(self):
        """Collect current database metrics."""
        if self.db_client is None or self.db_client.pool is None:
            return
        
        try:
            # Get pool stats from asyncpg pool
            pool = self.db_client.pool
            
            # Connection pool metrics
            # asyncpg pool attributes
            if hasattr(pool, '_minsize') and hasattr(pool, '_maxsize'):
                min_size = pool._minsize
                max_size = pool._maxsize
                
                # asyncpg internal: _usedcount, _reservesize
                used = getattr(pool, '_usedcount', 0)
                reserved = getattr(pool, '_reservesize', 0)
                idle = max(0, pool._maxsize - used - reserved) if hasattr(pool, '_maxsize') else 0
                
                host = os.environ.get('DB_HOST', 'localhost')
                database = os.environ.get('DB_NAME', 'face_recognition')
                
                self.db_connections_active.labels(host=host, database=database).set(used)
                self.db_connections_idle.labels(host=host, database=database).set(idle)
                
                # Pool utilization
                if max_size > 0:
                    utilization = (used / max_size) * 100
                    self.db_pool_utilization.labels(pool_name='primary').set(utilization)
            
            # Query individual metrics using system queries
            async with pool.acquire() as conn:
                # Active connections
                active_conn = await conn.fetchval(
                    "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                idle_conn = await conn.fetchval(
                    "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'idle'"
                )
                
                # Update metrics
                self.db_connections_active.labels(
                    host=host, database=database
                ).set(active_conn or 0)
                self.db_connections_idle.labels(
                    host=host, database=database
                ).set(idle_conn or 0)
                
                # Replication lag (if replica)
                await self._check_replication_lag(conn)
                
                # pg_stat_statements (if available)
                await self._collect_query_stats(conn)
                
        except Exception as e:
            logger.error(f"Failed to collect DB metrics: {e}", exc_info=True)
    
    async def _check_replication_lag(self, conn):
        """Check replication lag for read replicas."""
        try:
            # Check primary's view of replication lag
            result = await conn.fetch("""
                SELECT 
                    application_name,
                    client_addr,
                    pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn) as lag_bytes,
                    CAST(pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn) / 1024 / 1024 AS INTEGER) as lag_mb,
                    state
                FROM pg_stat_replication
                WHERE state = 'streaming'
            """)
            
            for row in result:
                lag_bytes = row['lag_bytes'] or 0
                lag_seconds = lag_bytes / 16 / 1024  # Approximate: 16KB per WAL record, 1024 per MB
                
                replica_name = row['application_name'] or row['client_addr'] or 'replica'
                self.db_replication_lag_seconds.labels(
                    replica_name=str(replica_name)
                ).set(lag_seconds)
                
                if lag_seconds > self.replication_lag_threshold_sec:
                    alert = Alert(
                        severity=AlertSeverity.WARNING,
                        metric_name='replication_lag',
                        message=f"Replication lag on {replica_name}: {lag_seconds:.1f}s",
                        context={
                            'replica': replica_name,
                            'lag_seconds': lag_seconds,
                            'threshold': self.replication_lag_threshold_sec
                        }
                    )
                    self._trigger_alert(alert)
                    
        except Exception as e:
            # pg_stat_replication doesn't exist or no replicas
            logger.debug(f"Replication check skipped: {e}")
    
    async def _collect_query_stats(self, conn):
        """Collect query statistics from pg_stat_statements."""
        try:
            # Check if extension is available
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
            )
            if not exists:
                return
            
            # Reset statistics periodically to focus on recent activity
            await conn.execute("SELECT pg_stat_statements_reset()")
            
        except Exception as e:
            logger.debug(f"pg_stat_statements check failed: {e}")
    
    def track_query(self, query: str, execution_time_ms: float, 
                    rows_returned: int, query_type: str = 'SELECT'):
        """Track a query execution (call from query wrapper/interceptor)."""
        
        # Record in history
        query_metrics = QueryMetrics(
            query=query.strip()[:200],  # Truncate for storage
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            timestamp=datetime.utcnow()
        )
        self._query_history.append(query_metrics)
        
        # Trim history
        if len(self._query_history) > self._max_query_history:
            self._query_history = self._query_history[-self._max_query_history:]
        
        # Update Prometheus metrics
        host = os.environ.get('DB_HOST', 'localhost')
        database = os.environ.get('DB_NAME', 'face_recognition')
        
        self.db_queries_total.labels(
            query_type=query_type, host=host, database=database
        ).inc()
        
        self.db_queries_duration_seconds.labels(
            query_type=query_type, host=host, database=database
        ).observe(execution_time_ms / 1000.0)
        
        # Check slow query threshold
        if execution_time_ms > self.slow_query_threshold_ms:
            self.db_slow_queries.labels(
                query_type=query_type, host=host, database=database
            ).inc()
            
            alert = Alert(
                severity=AlertSeverity.WARNING,
                metric_name='slow_query',
                message=f"Slow query detected: {query[:100]} took {execution_time_ms:.1f}ms",
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
        if self.db_client is None or self.db_client.pool is None:
            return
        
        try:
            pool = self.db_client.pool
            host = os.environ.get('DB_HOST', 'localhost')
            database = os.environ.get('DB_NAME', 'face_recognition')
            
            # Check pool exhaustion
            if hasattr(pool, '_maxsize') and hasattr(pool, '_usedcount'):
                max_size = pool._maxsize
                used = pool._usedcount
                
                if max_size > 0 and used > 0:
                    utilization_pct = (used / max_size) * 100
                    
                    if utilization_pct >= self.pool_exhaustion_threshold_pct:
                        alert = Alert(
                            severity=AlertSeverity.CRITICAL,
                            metric_name='pool_exhaustion',
                            message=f"Connection pool {utilization_pct:.1f}% full ({used}/{max_size} connections)",
                            context={
                                'pool': 'primary',
                                'active_connections': used,
                                'max_connections': max_size,
                                'utilization_pct': utilization_pct
                            }
                        )
                        self._trigger_alert(alert)
            
            # Check long-running queries
            async with pool.acquire() as conn:
                long_queries = await conn.fetch("""
                    SELECT 
                        pid,
                        query,
                        state,
                        now() - query_start AS duration,
                        age(backend_start, now()) AS session_duration
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                      AND query_start IS NOT NULL 
                      AND now() - query_start > interval '30 seconds'
                      AND pid <> pg_backend_pid()
                """)
                
                for row in long_queries:
                    alert = Alert(
                        severity=AlertSeverity.WARNING,
                        metric_name='long_running_query',
                        message=f"Long query running for {row['duration']}: {row['query'][:100]}",
                        context={
                            'pid': row['pid'],
                            'duration_seconds': row['duration'].total_seconds(),
                            'query': row['query'][:500]
                        }
                    )
                    self._trigger_alert(alert)
                
                # Check for bloat in tables (optional)
                # This is expensive, run less frequently
                pass
                
        except Exception as e:
            logger.error(f"Error checking thresholds: {e}", exc_info=True)
    
    def _trigger_alert(self, alert: Alert):
        """Trigger an alert and invoke callbacks."""
        self._alerts.append(alert)
        logger.warning(f"ALERT [{alert.severity.value.upper()}] {alert.message}")
        
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
        return generate_latest(REGISTRY)
    
    def get_query_performance_report(self, last_minutes: int = 10) -> Dict[str, Any]:
        """Generate query performance report."""
        cutoff = datetime.utcnow() - timedelta(minutes=last_minutes)
        recent_queries = [q for q in self._query_history if q.timestamp >= cutoff]
        
        if not recent_queries:
            return {"message": "No queries recorded in the time window"}
        
        total_queries = len(recent_queries)
        avg_time = sum(q.execution_time_ms for q in recent_queries) / total_queries
        max_time = max(q.execution_time_ms for q in recent_queries)
        slow_queries = [q for q in recent_queries 
                       if q.execution_time_ms > self.slow_query_threshold_ms]
        
        # Group by query type (first word)
        query_types: Dict[str, List[float]] = {}
        for q in recent_queries:
            qtype = q.query.split()[0] if q.query.split() else 'UNKNOWN'
            query_types.setdefault(qtype, []).append(q.execution_time_ms)
        
        query_type_stats = {}
        for qtype, times in query_types.items():
            query_type_stats[qtype] = {
                'count': len(times),
                'avg_ms': sum(times) / len(times),
                'max_ms': max(times)
            }
        
        return {
            'time_window_minutes': last_minutes,
            'total_queries': total_queries,
            'avg_execution_time_ms': avg_time,
            'max_execution_time_ms': max_time,
            'slow_queries_count': len(slow_queries),
            'slow_query_threshold_ms': self.slow_query_threshold_ms,
            'query_type_breakdown': query_type_stats,
            'slowest_queries': sorted(
                recent_queries, 
                key=lambda q: q.execution_time_ms, 
                reverse=True
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


def init_monitor(db_client=None):
    """Initialize global monitor with DB client."""
    global _monitor
    _monitor = DatabaseMonitor(db_client)
    return _monitor
