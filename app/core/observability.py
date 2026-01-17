import logging

import phoenix as px
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

logger = logging.getLogger(__name__)

def init_observability():
    """
    Initializes Arize Phoenix for local observability using OpenInference.
    This provides deep tracing for LlamaIndex Workflows, Agents, and RAG.
    """
    try:
        px.launch_app()

        endpoint = "http://127.0.0.1:6006/v1/traces"
        tracer_provider = trace_sdk.TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))

        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info("🔭 Arize Phoenix Observability initialized.")
        logger.info("   View traces at: http://localhost:6006")

    except Exception as e:
        logger.warning(f"Failed to initialize Arize Phoenix: {e}")
