import logging

from opentelemetry.instrumentation.logging import LoggingInstrumentor


def configure_logging():
    LoggingInstrumentor().instrument(set_logging_format=True)
    return logging.getLogger(__name__)