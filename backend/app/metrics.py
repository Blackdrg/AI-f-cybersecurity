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

# Enrichment metrics
enrichment_requests = Counter(
    'enrichment_requests_total', 'Total enrichment requests')
enrichment_latency = Histogram(
    'enrichment_latency_seconds', 'Enrichment latency')


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
