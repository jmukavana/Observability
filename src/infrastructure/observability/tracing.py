import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.infrastructure.observability.resource import get_resource


def configure_tracing():
    trace.set_tracer_provider(TracerProvider(resource=get_resource()))

    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        f"{os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4318')}/v1/traces",
    )
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
    )
    processor = BatchSpanProcessor(exporter)

    trace.get_tracer_provider().add_span_processor(processor)
    return trace.get_tracer(__name__)
