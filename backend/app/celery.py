"""
Celery Configuration for AI-f Background Tasks
Task routing, retry policies, and monitoring setup
"""
import os
from celery import Celery
from celery.schedules import crontab

# Redis broker URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
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
    ]
)

# Configuration
app.conf.update(
    # Task routing strategy
    task_routes={
        "app.tasks.recognition_tasks.*": {"queue": "recognition", "priority": 9},
        "app.tasks.model_training_tasks.*": {"queue": "training", "priority": 5},
        "app.tasks.enrichment_tasks.*": {"queue": "enrichment", "priority": 6},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance", "priority": 1},
        "app.tasks.federated_learning_tasks.*": {"queue": "federated", "priority": 3},
    },
    # Task acknowledgment and time limits
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    # Worker settings
    worker_prefetch_multiplier=1,  # One task per worker at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_send_task_events=True,
    # Result settings
    result_expires=86400,  # 24 hours
    result_backend=REDIS_URL,
    result_serializer="json",
    accept_content=["json"],
    # Task default settings
    task_default_retry_delay=60,  # 1 minute
    task_default_max_retries=3,
    task_soft_time_limit_task=None,
    # Monitoring
    task_send_sent_event=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "model-health-check-every-hour": {
            "task": "app.tasks.maintenance_tasks.check_model_health",
            "schedule": crontab(minute=0, hour="*"),
        },
        "audit-chain-verification-daily": {
            "task": "app.tasks.maintenance_tasks.verify_audit_chain_integrity",
            "schedule": crontab(minute=0, hour=2),  # 2 AM daily
        },
        "federated-learning-round-nightly": {
            "task": "app.tasks.federated_learning_tasks.trigger_federated_round",
            "schedule": crontab(minute=0, hour=3),  # 3 AM nightly
        },
        "stale-session-cleanup": {
            "task": "app.tasks.maintenance_tasks.cleanup_stale_sessions",
            "schedule": crontab(minute=30, hour="*/6"),  # Every 6 hours
        },
        "bias-report-generation": {
            "task": "app.tasks.enrichment_tasks.generate_bias_report",
            "schedule": crontab(minute=0, hour=9),  # Daily at 9 AM
        },
    },
    beat_schedule_filename="celerybeat-schedule",
    beat_max_loop_interval=5,
)

# Task default retry policy
app.conf.task_default_retry_policy = {
    "max_retries": 3,
    "interval_start": 0,  # Start retrying immediately
    "interval_step": 60,  # Wait 1 minute between retries
    "interval_max": 300,  # Maximum 5 minutes between retries
}

# Task annotations for specific retry behavior
app.conf.task_annotations = {
    "app.tasks.recognition_tasks.*": {"max_retries": 5, "retry_backoff": True},
    "app.tasks.model_training_tasks.*": {"max_retries": 2, "retry_backoff": True},
}

# Enable SSL for Redis if needed
if os.getenv("REDIS_SSL", "false").lower() == "true":
    app.conf.broker_use_ssl = {
        "ssl_cert_reqs": "required",
        "ssl_ca_certs": os.getenv("REDIS_CA_CERT", "/etc/ssl/certs/ca.crt"),
    }
    app.conf.redis_backend_use_ssl = app.conf.broker_use_ssl

# Custom task base class with monitoring
from celery import Task

class MonitoredTask(Task):
    """Base task class that records metrics."""
    
    def on_success(self, retval, task_id, args, kwargs):
        from app.metrics import tasks_successful, tasks_failed
        tasks_successful.inc()
        super().on_success(retval, task_id, args, kwargs)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from app.metrics import tasks_failed
        tasks_failed.inc()
        super().on_failure(exc, task_id, args, kwargs, einfo)

app.Task = MonitoredTask

# Initialize Celery app
celery_app = app
