"""
Celery configuration with retry logic, dead-letter queue, and task time limits.
"""
from celery import Celery
from celery.schedules import crontab
import os

# Create Celery app
app = Celery(
    'face_recognition',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1'),
    include=['app.services.queue_manager', 'app.services.recognition_tasks']
)

# Configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings - optimized for low latency
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    worker_max_tasks_per_child=1000,  # Prevent memory leaks
    worker_max_memory_per_child=200000,  # 200MB soft limit
    
    # Task acknowledgment - ensures tasks aren't lost if worker crashes
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Task time limits (hard/soft)
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit (raises SoftTimeLimitExceeded)
    
    # Result expiration (keep results for 1 hour)
    result_expires=3600,
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'recognition': {
            'exchange': 'recognition',
            'routing_key': 'recognition',
        },
        'enrollment': {
            'exchange': 'enrollment',
            'routing_key': 'enrollment',
        },
        'maintenance': {
            'exchange': 'maintenance',
            'routing_key': 'maintenance',
        },
        'dead_letter': {
            'exchange': 'dead_letter',
            'routing_key': 'dead_letter',
        },
    },
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # Retry configuration
    task_default_retry_delay=60,  # Wait 60 seconds before retry
    task_default_max_retries=3,  # Max 3 retries
    
    # Monitor with Flower
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Redis specific settings
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 hour
        'fanout_prefix': True,
        'fanout_patterns': True,
        'priority_steps': [0, 1, 2],
        'queue_order_strategy': 'priority',
    },
    result_backend_transport_options={
        'visibility_timeout': 3600,
    },
)

# Task routing (send high-priority tasks to recognition queue)
app.conf.task_routes = {
    'app.services.recognition_tasks.recognize_face': {'queue': 'recognition'},
    'app.services.recognition_tasks.multi_camera_fuse': {'queue': 'recognition'},
    'app.services.queue_manager.process_frame': {'queue': 'recognition'},
    'app.services.enrollment_tasks.enroll_person': {'queue': 'enrollment'},
    'app.services.maintenance_tasks.cleanup_old_data': {'queue': 'maintenance'},
}

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-recognitions': {
        'task': 'app.services.maintenance_tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        'options': {'queue': 'maintenance'},
    },
    'health-check-cameras': {
        'task': 'app.services.maintenance_tasks.check_camera_health',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'maintenance'},
    },
}


def setup_celery_signals():
    """Setup Celery signals for monitoring and retry logic."""
    from celery.signals import task_failure, task_success, task_retry, task_revoked
    
    @task_failure.connect
    def on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, **other):
        """Log task failures and send to dead-letter queue if max retries exceeded."""
        from celery import current_app
        logger = current_app.log.get_default_logger()
        
        logger.error(
            f"Task {sender.name}[{task_id}] failed after {sender.request.retries} retries",
            extra={
                "task_id": task_id,
                "task": sender.name,
                "exception": str(exception),
                "args": args,
                "kwargs": kwargs,
            }
        )
        
        # If max retries exceeded, move to dead-letter queue
        if sender.request.retries >= sender.max_retries:
            logger.warning(f"Task {task_id} exceeded max retries, sending to dead-letter queue")
            # Re-queue to dead-letter with original arguments for manual inspection
            sender.apply_async(args=args, kwargs=kwargs, queue='dead_letter')
    
    @task_success.connect
    def on_task_success(sender=None, result=None, **kwargs):
        """Log successful task completion."""
        logger = sender.app.log.get_default_logger()
        logger.info(
            f"Task {sender.name}[{sender.request.id}] completed successfully",
            extra={"task_id": sender.request.id, "task": sender.name}
        )
    
    @task_retry.connect
    def on_task_retry(sender=None, reason=None, **kwargs):
        """Log task retry attempts."""
        logger = sender.app.log.get_default_logger()
        logger.warning(
            f"Task {sender.name}[{sender.request.id}] retrying (attempt {sender.request.retries})",
            extra={
                "task_id": sender.request.id,
                "task": sender.name,
                "retry_count": sender.request.retries,
                "reason": str(reason),
            }
        )


# Initialize signals when Celery starts
@app.on_after_configure.connect
def setup_signals(sender, **kwargs):
    setup_celery_signals()
