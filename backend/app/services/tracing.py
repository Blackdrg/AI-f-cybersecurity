import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer

def setup_tracing(app=None):
    """
    Sets up OpenTelemetry tracing for FastAPI and gRPC.
    """
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
    service_name = os.getenv("SERVICE_NAME", "ai-f-backend")
    
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })
    
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    if app:
        FastAPIInstrumentor.instrument_app(app)
    
    # Instrument gRPC
    GrpcInstrumentorServer().instrument()

def get_tracer():
    return trace.get_tracer(__name__)
