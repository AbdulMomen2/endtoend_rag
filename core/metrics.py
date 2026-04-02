"""
Prometheus metrics for observability.
Gracefully disabled if prometheus_client is not installed.
"""
import logging
logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

    query_counter = Counter(
        "rag_queries_total", "Total RAG queries",
        ["session_type"]  # labels: "rag", "conversational", "fallback"
    )
    latency_histogram = Histogram(
        "rag_query_latency_seconds", "End-to-end query latency",
        buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    retrieval_histogram = Histogram(
        "rag_retrieval_latency_seconds", "Retrieval latency",
        buckets=[0.05, 0.1, 0.2, 0.5, 1.0]
    )
    active_sessions = Gauge("rag_active_sessions", "Number of active sessions")
    ingestion_counter = Counter("rag_ingestions_total", "Total document ingestions")
    fallback_counter = Counter("rag_fallbacks_total", "Total fallback responses triggered")

    METRICS_ENABLED = True
    logger.info("Prometheus metrics enabled.")

except ImportError:
    METRICS_ENABLED = False
    logger.info("prometheus_client not installed. Metrics disabled.")

    # Stub objects so code doesn't break
    class _Stub:
        def labels(self, **kwargs): return self
        def inc(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def set(self, *a, **kw): pass

    query_counter = _Stub()
    latency_histogram = _Stub()
    retrieval_histogram = _Stub()
    active_sessions = _Stub()
    ingestion_counter = _Stub()
    fallback_counter = _Stub()
    generate_latest = lambda: b""
    CONTENT_TYPE_LATEST = "text/plain"
