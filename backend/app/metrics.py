from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Metrics
recognition_count = Counter(
    'face_recognition_requests_total', 'Total recognition requests')
enroll_count = Counter('face_enroll_requests_total', 'Total enroll requests')
recognition_latency = Histogram(
    'face_recognition_latency_seconds', 'Recognition latency')
enroll_latency = Histogram('face_enroll_latency_seconds', 'Enroll latency')
false_accepts = Counter('face_false_accepts_total', 'False accepts')
false_rejects = Counter('face_false_rejects_total', 'False rejects')
index_size = Gauge('face_index_size', 'Current index size')

# Enterprise SLA Metrics
error_count = Counter('ai_f_errors_total', 'Total errors', ['error_type', 'org_id'])
active_streams = Gauge('ai_f_active_streams_total', 'Current active processing streams')
circuit_breaker_state = Gauge('ai_f_circuit_breaker_state', 'State of circuit breakers (0=Closed, 1=Open)', ['service'])
spoof_attempts = Counter('ai_f_spoof_attempts_total', 'Total spoof attempts detected', ['org_id'])
db_connection_status = Gauge('ai_f_db_connection_status', 'Database connection status (1=Healthy, 0=Unhealthy)')
latency_percentile = Histogram('ai_f_request_latency_seconds', 'Request latency with percentiles', buckets=(.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0))

# Enrichment metrics
enrichment_requests = Counter(
    'enrichment_requests_total', 'Total enrichment requests')
enrichment_latency = Histogram(
    'enrichment_latency_seconds', 'Enrichment latency')

# Celery task metrics
tasks_successful = Counter('celery_tasks_successful_total', 'Total successful Celery tasks')
tasks_failed = Counter('celery_tasks_failed_total', 'Total failed Celery tasks')
task_duration_seconds = Histogram('celery_task_duration_seconds', 'Task execution duration', ['task_name'])



def setup_metrics(app):
    from fastapi import Response
    from fastapi.routing import APIRoute

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type="text/plain")

    # Middleware to measure latency
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
