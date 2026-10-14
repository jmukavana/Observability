import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from src.infrastructure.observability.resource import get_resource


def configure_metrics():
    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        f"{os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4318')}/v1/metrics",
    )
    exporter = OTLPMetricExporter(
        endpoint=endpoint,
    )
    reader = PeriodicExportingMetricReader(exporter)

    metrics.set_meter_provider(
        MeterProvider(resource=get_resource(), metric_readers=[reader])
    )
    meter = metrics.get_meter(__name__)
    request_counter = meter.create_counter(
        "custom_request_counter",
        description="Count API requests",
    )
    return request_counter
