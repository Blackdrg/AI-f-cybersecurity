"""
Celery Configuration for AI-f - Production with all task modules
"""
import os
import logging
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

app = Celery(
    "ai_f_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.recognition_tasks",
        "app.tasks.model_training_tasks",
        "app.tasks.enrichment_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.federated_learning_tasks",
        "app.tasks.payment_tasks",
        "app.tasks.anchoring_tasks",
        "app.tasks.compliance_tasks",
        "app.tasks.threat_intel_tasks",
    ]
)

app.conf.update(
    task_routes={
        "app.tasks.recognition_tasks.*": {"queue": "recognition", "priority": 9},
        "app.tasks.model_training_tasks.*": {"queue": "training", "priority": 5},
        "app.tasks.enrichment_tasks.*": {"queue": "enrichment", "priority": 6},
        "app.tasks.threat_intel_tasks.*": {"queue": "threat_intel", "priority": 7},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance", "priority": 1},
        "app.tasks.federated_learning_tasks.*": {"queue": "federated", "priority": 3},
        "app.tasks.payment_tasks.*": {"queue": "payments", "priority": 7},
        "app.tasks.anchoring_tasks.*": {"queue": "anchoring", "priority": 4},
        "app.tasks.compliance_tasks.*": {"queue": "compliance", "priority": 2},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_default_retry_delay=60,
    task_default_max_retries=3,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_send_task_events=True,
    worker_disable_rate_limits=False,
    worker_max_memory_per_child=512000000,
    result_expires=86400,
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={
        "model-health-check": {
            "task": "app.tasks.maintenance_tasks.check_model_health",
            "schedule": crontab(minute=0, hour="*"),
        },
        "audit-chain-verification": {
            "task": "app.tasks.maintenance_tasks.verify_audit_chain_integrity",
            "schedule": crontab(minute=0, hour=2),
        },
        "federated-learning-round": {
            "task": "app.tasks.federated_learning_tasks.trigger_federated_round",
            "schedule": crontab(minute=0, hour=3),
        },
        "stale-session-cleanup": {
            "task": "app.tasks.maintenance_tasks.cleanup_stale_sessions",
            "schedule": crontab(minute=30, hour="*/6"),
        },
        "bias-report-generation": {
            "task": "app.tasks.enrichment_tasks.generate_bias_report",
            "schedule": crontab(minute=0, hour=9),
        },
        "usage-audit": {
            "task": "app.tasks.maintenance_tasks.run_usage_audit",
            "schedule": crontab(hour=2, minute=0),
        },
        "data-retention-enforcement": {
            "task": "app.tasks.compliance_tasks.enforce_data_retention",
            "schedule": crontab(hour=4, minute=0),
        },
        "cache-invalidation": {
            "task": "app.tasks.maintenance_tasks.invalidate_expired_cache",
            "schedule": crontab(minute="*/15"),
        },
        "db-vacuum-analyze": {
            "task": "app.tasks.maintenance_tasks.run_db_maintenance",
            "schedule": crontab(hour=1, minute=0, day_of_week=0),
        },
        "refresh-urlhaus-feed": {
            "task": "app.tasks.threat_intel_tasks.refresh_urlhaus_feed",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "refresh-otx-pulses": {
            "task": "app.tasks.threat_intel_tasks.refresh_otx_pulses",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "refresh-emerging-threats": {
            "task": "app.tasks.threat_intel_tasks.refresh_emerging_threats",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "refresh-stix-taxii-feeds": {
            "task": "app.tasks.threat_intel_tasks.refresh_stix_taxii_feeds",
            "schedule": crontab(minute=0, hour="*/12"),
        },
        "expire-old-iocs": {
            "task": "app.tasks.threat_intel_tasks.expire_old_iocs",
            "schedule": crontab(hour=6, minute=0),
        },
        "deduplicate-iocs": {
            "task": "app.tasks.threat_intel_tasks.deduplicate_iocs",
            "schedule": crontab(hour=12, minute=0),
        },
        "ioc-enrichment-report": {
            "task": "app.tasks.threat_intel_tasks.ioc_enrichment_report",
            "schedule": crontab(hour=8, minute=0),
        },
    },
    task_dead_letter_queue="dead_letter",
    task_default_delivery_mode=2,
    broker_transport_options={
        "visibility_timeout": 3600,
        "fanout_prefix": True,
        "fanout_patterns": True,
    },
    task_send_sent_event=True,
    task_send_publish_sent_event=True,
    task_track_started=True,
    broker_use_ssl=False,
    redis_backend_use_ssl=False,
)

if os.getenv("REDIS_SSL", "false").lower() == "true":
    app.conf.broker_use_ssl = {
        "ssl_cert_reqs": "required",
        "ssl_ca_certs": os.getenv("REDIS_CA_CERT", "/etc/ssl/certs/ca.crt"),
    }
    app.conf.redis_backend_use_ssl = app.conf.broker_use_ssl


class MonitoredTask(object):
    """Base task with monitoring."""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("Task {} completed successfully".format(task_id))
        try:
            from app.metrics import tasks_successful
            tasks_successful.inc()
        except Exception:
            pass

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("Task {} retry: {}".format(task_id, exc))

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Task {} failed: {}".format(task_id, exc), exc_info=True)
        try:
            from app.metrics import tasks_failed
            tasks_failed.inc()
        except Exception:
            pass


celery_app = app