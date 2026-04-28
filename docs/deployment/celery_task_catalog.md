# Celery Task Catalog & Queue Topology

## Overview

AI-f uses Celery with Redis as the message broker for asynchronous background job processing.
This document catalogs all tasks, their routing, retry policies, and monitoring.

---

## Queue Topology

Four dedicated queues with separate workers for isolation:

```
┌─────────────────────────────────────────────┐
│         Redis Message Broker                │
├─────────────────────────────────────────────┤
│  Queue: recognition      (high priority)    │
│  Queue: training         (CPU-intensive)   │
│  Queue: maintenance      (low priority)     │
│  Queue: federated        (FL coordination) │
└─────────────────────────────────────────────┘
         ↓           ↓            ↓           ↓
    ┌────────┐ ┌─────────┐ ┌───────────┐ ┌─────────┐
    │ Worker │ │ Worker  │ │ Worker    │ │ Worker  │
    │  (x3)  │ │  (x2)   │ │   (x1)    │ │  (x2)   │
    └────────┘ └─────────┘ └───────────┘ └─────────┘
    Concurrency: 4  Concurrency: 2  Concurrency: 1  Concurrency: 2
    Prefetch: 4     Prefetch: 2     Prefetch: 1    Prefetch: 2
```

**Worker Deployment (Docker Compose / K8s):**
```yaml
# In docker-compose.prod.yml
celery-recognition:
  command: celery -A backend.celery worker -Q recognition --concurrency=4
  scale: 3  # 12 total processes

celery-training:
  command: celery -A backend.celery worker -Q training --concurrency=2
  scale: 2

celery-maintenance:
  command: celery -A backend.celery worker -Q maintenance --concurrency=1
  scale: 1

celery-federated:
  command: celery -A backend.celery worker -Q federated --concurrency=2
  scale: 2
```

---

## Task Catalog

### 1. Recognition Queue (`recognition`)

**Priority:** HIGH — user-facing API responses depend on these

| Task | Module | Purpose | Timeout | Retries |
|------|--------|---------|---------|---------|
| `process_recognition_batch` | tasks.recognition_tasks | Batch face recognition on image batches | 60s | 5 (exponential) |
| `enroll_person_async` | tasks.recognition_tasks | Async multi-modal enrollment (face+voice+gait) | 120s | 3 |
| `process_video_recognition` | tasks.recognition_tasks | Frame-by-frame video recognition | 600s (10min) | 3 |

**Routing:** All `/api/recognize` and `/api/enroll` POST requests → `recognition` queue
**Prefetch:** 4 tasks per worker process (to avoid starving other queues)

---

### 2. Training Queue (`training`)

**Priority:** MEDIUM — model improvement, not user-facing

| Task | Module | Purpose | Timeout | Retries |
|------|--------|---------|---------|---------|
| `retrain_model_async` | tasks.model_training_tasks | Retrain model on new dataset | 1h | 2 |
| `evaluate_model_pipeline` | tasks.model_training_tasks | Full evaluation on test set | 30min | 2 |
| `export_model_to_onnx` | tasks.model_training_tasks | Convert PyTorch → ONNX for edge | 15min | 2 |
| `publish_model_to_registry` | tasks.model_training_tasks | Publish model version to registry | 5min | 3 |

**Routing:** Admin-triggered via `/api/admin/models/retrain`
**Schedule:** `retrain_model_async` runs weekly via Celery Beat

---

### 3. Maintenance Queue (`maintenance`)

**Priority:** LOW — housekeeping tasks

| Task | Module | Purpose | Timeout | Retries |
|------|--------|---------|---------|---------|
| `cleanup_stale_sessions` | tasks.recognition_tasks | Delete expired sessions, cache | 5min | 2 |
| `verify_audit_chain_integrity` | tasks.recognition_tasks | Daily hash-chain + ZKP verification | 10min | 2 |
| `rotate_encryption_keys` | tasks.maintenance_tasks | Key rotation workflow | 15min | 1 |
| `purge_expired_consents` | tasks.maintenance_tasks | Remove expired BIPA consents | 5min | 1 |
| `aggregate_daily_metrics` | tasks.maintenance_tasks | Roll up Prometheus metrics to DB | 10min | 2 |
| `backup_model_registry` | tasks.maintenance_tasks | S3 backup of model_versions table | 20min | 1 |

**Schedule:** Most run daily at 02:00 UTC via Celery Beat
**Concurrency:** 1 worker (sequential to avoid DB lock contention)

---

### 4. Federated Learning Queue (`federated`)

**Priority:** MEDIUM — client coordination

| Task | Module | Purpose | Timeout | Retries |
|------|--------|---------|---------|---------|
| `aggregate_federated_updates` | tasks.federated_learning_tasks | Secure aggregation of client gradients | 5min | 3 |
| `trigger_federated_round` | tasks.federated_learning_tasks | Orchestrate new FL round | 2min | 3 |
| `distribute_model_update` | tasks.federated_learning_tasks | OTA model distribution to edge devices | 10min | 2 |
| `verify_client_update` | tasks.federated_learning_tasks | ZKP verification of client update correctness | 30s | 3 |

**Routing:** Triggered by FL orchestrator, not user requests
**Security:** Tasks require `service:fl` token, not user JWT

---

## Task Monitoring & Metrics

### Prometheus Metrics

All tasks emit these metrics:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `celery_tasks_total` | counter | task_name, status | Total tasks executed |
| `celery_task_duration_seconds` | histogram | task_name | Task execution time |
| `celery_queue_length` | gauge | queue_name | Current queue depth |
| `celery_workers_active` | gauge | queue_name | Active workers per queue |

**Grafana Dashboard:** `k8s/grafana/dashboards/ai-f-celery.json`

---

### Flower (Optional)

Flower UI available at `http://localhost:5555` for task inspection:

```bash
# Run Flower
celery -A backend.celery flower --port=5555
```

**Shows:**
- Worker status (online/offline)
- Queue lengths
- Task statistics (success/failure rates)
- Task details (arguments, results, traceback)

---

## Task Result Backend

**Redis** (configured via `CELERY_RESULT_BACKEND`):
- Results expire after 1 day (`result_expires=86400`)
- Only failures stored indefinitely for debugging
- Successes transient (garbage collected)

---

## Error Handling & Retries

All tasks inherit `MonitoredTask` base class:

```python
class MonitoredTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        tasks_successful.inc()  # Prometheus counter
        super().on_success(...)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        tasks_failed.inc()
        logger.error(f"Task {task_id} failed: {exc}", exc_info=True)
        super().on_failure(...)
```

**Retry Strategies:**

| Task Type | Base Delay | Backoff | Max Retries |
|-----------|-----------|---------|-------------|
| Recognition | 60s | 2× each retry | 5 (max 32 min) |
| Enrollment | 120s | 2× | 3 (max 8 min) |
| Training | 600s (10min) | static | 2 |
| Maintenance | 300s (5min) | static | 2 |
| FL tasks | 300-600s | static | 2-3 |

**Exponential backoff example:** 60s → 120s → 240s → 480s → 960s (cap at 3600s)

---

## Periodic Tasks (Celery Beat)

Scheduled in `backend/app/celery.py`:

| Schedule | Task | Purpose |
|----------|------|---------|
| Daily 02:00 UTC | `cleanup_stale_sessions` | Delete expired sessions (24h+) |
| Daily 03:00 UTC | `verify_audit_chain_integrity` | Daily integrity check |
| Daily 04:00 UTC | `aggregate_daily_metrics` | Roll up day's metrics |
| Weekly Sun 05:00 UTC | `retrain_model_async` | Weekly model retraining |
| Hourly | `purge_expired_consents` | Remove old BIPA consents |

---

## Celery Configuration

**`backend/celery.py`:**

```python
app = Celery(
    'backend',
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
)

# Task routing
app.conf.task_routes = {
    'app.tasks.recognition_tasks.*': {'queue': 'recognition'},
    'app.tasks.model_training_tasks.*': {'queue': 'training'},
    'app.tasks.maintenance_tasks.*': {'queue': 'maintenance'},
    'app.tasks.federated_learning_tasks.*': {'queue': 'federated'},
}

# Global task defaults
app.conf.task_acks_late = True        # Acknowledge AFTER completion
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1  # One task at a time per worker
app.conf.worker_max_tasks_per_child = 1000  # Prevent memory leaks
```

---

## Dead Letter Queue (DLQ)

Failed tasks after max retries go to:
- **Redis key:** `celery` → `{queue}.dlq`
- **TTL:** 7 days (then auto-purged)
- **Alerting:** Slack alert when DLQ > 10 tasks

**Manual Replay:**
```bash
# List failed tasks
celery -A backend.app.celery inspect reserved

# Replay from DLQ
celery -A backend.app.celery shell -Q recognition.dlq
>>> from celery import current_app
>>> current_app.loader.import_default_modules()
>>> current_app.send_task('app.tasks.recognition_tasks.process_recognition_batch', args, kwargs)
```

---

## Task Administration

### Start All Workers (Development)

```bash
# In separate terminals or with tmux
celery -A backend.app.celery worker -Q recognition --concurrency=4 --loglevel=INFO
celery -A backend.app.celery worker -Q training --concurrency=2 --loglevel=INFO
celery -A backend.app.celery worker -Q maintenance --concurrency=1 --loglevel=INFO
celery -A backend.app.celery worker -Q federated --concurrency=2 --loglevel=INFO
```

### Start with Supervisor (Production)

```ini
[program:celery-recognition]
command=celery -A backend.app.celery worker -Q recognition --concurrency=4
directory=/app
user=ai-f
autostart=true
autorestart=true
```

---

## Common Pitfalls & Solutions

| Symptom | Cause | Fix |
|---------|-------|-----|
| Tasks stuck in `started` state | Worker crashed before ack | Restart worker; `acks_late=True` means tasks re-queued |
| High memory usage | Prefetch too high | Set `worker_prefetch_multiplier=1` |
| Queue backlog | Not enough workers | Scale out horizontally |
| Task timeout | Long-running model training | Increase `task_time_limit` or break into subtasks |
| Duplicate execution | Worker died after processing but before ack | Make tasks idempotent (use `task_id` dedup) |

---

## Idempotency

All tasks are designed to be safely retried:
- Enrollments use `person_id` as idempotency key → duplicate creates same result
- Model training writes to temp file then atomic rename
- Audit verification reads-only

---

## Observability

**Structured logs (JSON):**
```json
{
  "timestamp": "2026-04-28T12:00:00Z",
  "task": "process_recognition_batch",
  "task_id": "abc123",
  "status": "started",
  "queue": "recognition",
  "worker": "celery@worker-1",
  "args_length": 5
}
```

**Sentry integration:** All task failures captured with full context

**Custom Metrics:**
- `ai_f_tasks_active{queue="recognition"}`
- `ai_f_tasks_failed_total{task="enroll_person_async"}`
- `ai_f_queue_depth{queue="training"}`
