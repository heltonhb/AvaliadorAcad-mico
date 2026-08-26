"""
OpenTelemetry tracing configuration for AnaliseTextos.
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def setup_telemetry(app) -> trace.Tracer | None:
    """
    Configure OpenTelemetry tracing.
    Returns tracer or None if telemetry is disabled.
    """
    # Check if telemetry is enabled
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        return None

    service_name = os.environ.get("OTEL_SERVICE_NAME", "analise-textos-api")
    service_version = os.environ.get("OTEL_SERVICE_VERSION", "6.0")

    # Create resource
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )

    # Add batch span processor
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="/api/health,/api/health/live,/api/health/ready,/api/config",
    )

    # Instrument HTTPX
    HTTPXClientInstrumentor().instrument()

    # Instrument Redis
    RedisInstrumentor().instrument()

    # Get tracer
    tracer = trace.get_tracer(__name__)

    return tracer


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get tracer instance."""
    return trace.get_tracer(name)


# Context propagation utilities
def inject_trace_context(headers: dict) -> dict:
    """Inject current trace context into headers for downstream calls."""
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict) -> trace.SpanContext | None:
    """Extract trace context from incoming headers."""
    propagator = TraceContextTextMapPropagator()
    ctx = propagator.extract(headers)
    return trace.get_current_span(ctx).get_span_context() if ctx else None


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get tracer instance."""
    return trace.get_tracer(name)


# Context propagation utilities
def inject_trace_context(headers: dict) -> dict:
    """Inject current trace context into headers for downstream calls."""
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict) -> trace.SpanContext | None:
    """Extract trace context from incoming headers."""
    propagator = TraceContextTextMapPropagator()
    ctx = propagator.extract(headers)
    return trace.get_current_span(ctx).get_span_context() if ctx else None