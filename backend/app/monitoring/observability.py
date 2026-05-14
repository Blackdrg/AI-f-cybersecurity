"""
Production Observability Module
Centralized logging, distributed tracing, error aggregation, and alerting.
"""
import os
import sys
import json
import logging
import logging.handlers
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

try:
    from opentelemetry import trace, context
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    context = None

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger("ai_f_observability")


# ──────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────

error_counter = Counter(
    'ai_f_errors_total',
    'Total errors',
    ['error_type', 'org_id', 'module']
)

error_rate = Counter(
    'ai_f_error_rate',
    'Error rate per minute',
    ['error_type']
)

request_trace_counter = Counter(
    'ai_f_request_traces_total',
    'Total request traces',
    ['endpoint', 'method', 'status']
)

distributed_trace_active = Gauge(
    'ai_f_distributed_traces_active',
    'Number of active distributed traces'
)

error_aggregation = Counter(
    'ai_f_error_aggregated',
    'Aggregated error counts by fingerprint',
    ['error_fingerprint', 'module']
)

# ──────────────────────────────────────────────
# Structured JSON Logger
# ──────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Produces structured JSON log entries for centralized logging."""

    def __init__(self, service_name: str = "ai-f", environment: str = "production"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace context if available
        span = getattr(record, 'otel_span', None)
        if span and OTEL_AVAILABLE:
            ctx = span.get_span_context()
            log_entry["trace_id"] = format(ctx.trace_id, '032x')
            log_entry["span_id"] = format(ctx.span_id, '016x')

        # Add custom fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        # Add exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_entry, default=str)


class CentralizedLogger:
    """Centralized logging handler with multiple sinks."""

    def __init__(self, service_name: str = "ai-f", environment: str = None):
        self.service_name = service_name
        self.environment = environment or os.getenv("ENVIRONMENT", "production")
        self._handlers: List[logging.Handler] = []
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup logging handlers for different sinks."""
        json_formatter = JSONFormatter(self.service_name, self.environment)

        # Console handler (structured JSON)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        self._handlers.append(console_handler)

        # File handler with rotation
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=os.getenv("LOG_FILE_PATH", "/var/log/ai-f/app.log"),
                maxBytes=int(os.getenv("LOG_MAX_BYTES", 100 * 1024 * 1024)),  # 100MB
                backupCount=int(os.getenv("LOG_BACKUP_COUNT", 10))
            )
            file_handler.setFormatter(json_formatter)
            self._handlers.append(file_handler)
        except Exception as e:
            logger.warning(f"File logging setup failed: {e}")

        # Syslog handler (for ELK/Logstash)
        syslog_host = os.getenv("SYSLOG_HOST")
        if syslog_host:
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=(syslog_host, int(os.getenv("SYSLOG_PORT", 514)))
                )
                syslog_handler.setFormatter(json_formatter)
                self._handlers.append(syslog_handler)
            except Exception as e:
                logger.warning(f"Syslog setup failed: {e}")

    def get_logger(self, name: str) -> logging.Logger:
        """Get configured logger instance."""
        logger = logging.getLogger(name)
        logger.handlers = self._handlers
        logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
        return logger


# ──────────────────────────────────────────────
# Distributed Tracing
# ──────────────────────────────────────────────

class TracingService:
    """Distributed tracing service using OpenTelemetry."""

    def __init__(self, service_name: str = "ai-f"):
        self.service_name = service_name
        self._tracer_provider = None
        self._initialized = False

    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry not available, tracing disabled")
            return

        if self._initialized:
            return

        otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
        sample_rate = float(os.getenv("TRACE_SAMPLE_RATE", "1.0"))

        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            "service.version": os.getenv("SERVICE_VERSION", "2.5.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        })

        self._tracer_provider = TracerProvider(resource=resource)

        # Sampling based on rate
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        sampler = TraceIdRatioBased(sample_rate)
        self._tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )

        # OTLP exporter with retry
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,
            timeout=10.0
        )
        processor = BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=1000,
        )
        self._tracer_provider.add_span_processor(processor)
        trace.set_tracer_provider(self._tracer_provider)

        # Error tracking callback
        def on_span_end(span):
            if span.status and span.status.status_code == StatusCode.ERROR:
                error_counter.labels(
                    error_type="span_error",
                    org_id=span.get_attribute("org_id") or "unknown",
                    module=span.name
                ).inc()

        self._tracer_provider.add_span_processor(
            BatchSpanProcessor(on_span_end)
        )

        self._initialized = True
        logger.info(f"Tracing initialized: {self.service_name} -> {otlp_endpoint}")

    def get_tracer(self, name: str):
        """Get a tracer for the given module name."""
        if not self._initialized or not OTEL_AVAILABLE:
            return None
        return trace.get_tracer(name)

    @contextmanager
    def start_span(self, name: str, attributes: Dict[str, Any] = None):
        """Start a new span with attributes."""
        if not OTEL_AVAILABLE or not self._initialized:
            yield None
            return

        tracer = trace.get_tracer(self.service_name)
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(str(key), str(value))
            yield span


# ──────────────────────────────────────────────
# Error Aggregation
# ──────────────────────────────────────────────

class ErrorAggregator:
    """Aggregates and categorizes errors for alerting."""

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self._error_buckets: Dict[str, List[datetime]] = {}
        self._alert_thresholds = {
            "critical": 10,    # 10 errors in window
            "high": 25,        # 25 errors in window
            "medium": 50,      # 50 errors in window
            "low": 100,        # 100 errors in window
        }

    def record_error(self, error_type: str, module: str, error_id: str = None):
        """Record an error occurrence."""
        fingerprint = f"{error_type}:{module}"
        now = datetime.utcnow()

        if fingerprint not in self._error_buckets:
            self._error_buckets[fingerprint] = []

        self._error_buckets[fingerprint].append(now)
        self._cleanup_old(fingerprint)

        count = len(self._error_buckets[fingerprint])
        severity = self._get_severity(count)

        error_aggregation.labels(
            error_fingerprint=fingerprint[:50],
            module=module
        ).inc()

        error_counter.labels(
            error_type=error_type,
            org_id="system",
            module=module
        ).inc()

        if severity in ("critical", "high"):
            logger.critical(f"Error burst detected: {fingerprint} - {count} errors in {self.window_seconds}s")

        return {
            "fingerprint": fingerprint,
            "count": count,
            "severity": severity,
            "threshold": self._alert_thresholds.get(severity)
        }

    def _cleanup_old(self, fingerprint: str):
        """Remove errors outside the time window."""
        cutoff = datetime.utcnow().timestamp() - self.window_seconds
        self._error_buckets[fingerprint] = [
            t for t in self._error_buckets[fingerprint]
            if t.timestamp() > cutoff
        ]

    def _get_severity(self, count: int) -> str:
        """Determine severity based on error count."""
        if count >= self._alert_thresholds["critical"]:
            return "critical"
        elif count >= self._alert_thresholds["high"]:
            return "high"
        elif count >= self._alert_thresholds["medium"]:
            return "medium"
        return "low"

    def get_error_summary(self) -> Dict[str, Any]:
        """Get current error summary."""
        now = datetime.utcnow()
        summary = {}

        for fingerprint, timestamps in self._error_buckets.items():
            self._error_buckets[fingerprint] = [
                t for t in timestamps if (now - t).total_seconds() < self.window_seconds
            ]
            count = len(self._error_buckets[fingerprint])
            if count > 0:
                summary[fingerprint] = {
                    "count": count,
                    "severity": self._get_severity(count),
                    "first_error": min(self._error_buckets[fingerprint]).isoformat(),
                    "last_error": max(self._error_buckets[fingerprint]).isoformat(),
                }

        return summary


# ──────────────────────────────────────────────
# Alert Rules Engine
# ──────────────────────────────────────────────

class AlertRule:
    """Configurable alerting rule."""

    def __init__(self, name: str, condition: Dict[str, Any],
                 severity: str, notification_channels: List[str]):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.channels = notification_channels
        self._last_fired = None

    def check(self, metric_value: float) -> bool:
        """Check if an alert should fire."""
        op = self.condition.get("op", ">")
        threshold = self.condition.get("threshold", 0)
        duration = self.condition.get("duration_seconds", 60)

        fired = False
        if op == ">" and metric_value > threshold:
            fired = True
        elif op == "<" and metric_value < threshold:
            fired = True
        elif op == ">=" and metric_value >= threshold:
            fired = True
        elif op == "==" and metric_value == threshold:
            fired = True

        if fired:
            if self._last_fired is None or \
                    (datetime.utcnow() - self._last_fired).total_seconds() > duration:
                self._last_fired = datetime.utcnow()
                return True

        return False


class AlertingService:
    """Central alerting service for operational monitoring."""

    DEFAULT_RULES = [
        AlertRule(
            name="pool_exhaustion",
            condition={"op": ">", "threshold": 90, "duration_seconds": 120},
            severity="critical",
            notification_channels=["pagerduty", "slack"]
        ),
        AlertRule(
            name="high_error_rate",
            condition={"op": ">", "threshold": 50, "duration_seconds": 60},
            severity="high",
            notification_channels=["slack", "email"]
        ),
        AlertRule(
            name="replication_lag",
            condition={"op": ">", "threshold": 5, "duration_seconds": 180},
            severity="critical",
            notification_channels=["pagerduty"]
        ),
        AlertRule(
            name="cpu_usage",
            condition={"op": ">", "threshold": 85, "duration_seconds": 300},
            severity="medium",
            notification_channels=["slack"]
        ),
        AlertRule(
            name="memory_usage",
            condition={"op": ">", "threshold": 90, "duration_seconds": 120},
            severity="high",
            notification_channels=["pagerduty", "slack"]
        ),
    ]

    def __init__(self):
        self.rules = self.DEFAULT_RULES.copy()
        self._notifiers: Dict[str, Any] = {}

    def add_rule(self, rule: AlertRule):
        """Add a custom alert rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str):
        """Remove an alert rule by name."""
        self.rules = [r for r in self.rules if r.name != rule_name]

    def check_all(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Check all rules against current metrics."""
        alerts = []
        for rule in self.rules:
            metric_name = rule.name
            if metric_name in metrics:
                if rule.check(metrics[metric_name]):
                    alerts.append({
                        "rule": rule.name,
                        "severity": rule.severity,
                        "value": metrics[metric_name],
                        "threshold": rule.condition["threshold"],
                        "channels": rule.channels,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        return alerts


# ──────────────────────────────────────────────
# Audit Dashboard Data Provider
# ──────────────────────────────────────────────

class AuditDashboardService:
    """Service providing data for audit and monitoring dashboards."""

    def __init__(self, db_client=None):
        self.db_client = db_client

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current system metrics snapshot for dashboard."""
        from app.monitoring.db_monitor import get_monitor
        monitor = get_monitor()

        prom_metrics = monitor.get_prometheus_metrics()
        prom_text = prom_metrics.decode('utf-8') if isinstance(prom_metrics, bytes) else str(prom_metrics)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "prometheus_metrics": self._parse_metrics(prom_text),
            "error_summary": ErrorAggregator().get_error_summary(),
            "trace_activity": distributed_trace_active._value.get(),
            "uptime_percent": self._calculate_uptime(),
        }

    def _parse_metrics(self, raw_metrics: str) -> Dict[str, Any]:
        """Parse Prometheus text metrics into structured data."""
        parsed = {}
        for line in raw_metrics.split('\n'):
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            try:
                if '{' in line:
                    name = line.split('{')[0]
                    rest = line.split('{')[1].split('}')[0]
                    value = float(line.split('}')[1].strip())
                    labels = {}
                    for pair in rest.split(','):
                        k, v = pair.split('=', 1)
                        labels[k.strip()] = v.strip().strip('"')
                    parsed[name] = parsed.get(name, []) + [{"labels": labels, "value": value}]
                else:
                    parts = line.rsplit(' ', 1)
                    if len(parts) == 2:
                        parsed[parts[0]] = float(parts[1])
            except Exception:
                continue
        return parsed

    def _calculate_uptime(self) -> float:
        """Calculate current uptime percentage (simulated)."""
        return 99.97  # In production, calculate from actual health checks