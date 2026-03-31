import json
import logging
import time
from typing import Any, Dict, List
from functools import wraps

class RAGAnalyticsLogger:
    """Structured JSON logger for RAG analytics and observability."""
    def __init__(self):
        self.logger = logging.getLogger("RAG_Analytics")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s') # Just the JSON string
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_interaction(self, session_id: str, query: str, response: str, 
                        sources: List[Dict], metrics: Dict[str, Any]):
        """Logs a complete RAG interaction for analytics."""
        log_payload = {
            "timestamp": time.time(),
            "event_type": "rag_inference",
            "session_id": session_id,
            "query": query,
            "response_length": len(response),
            "sources_retrieved": len(sources),
            "top_similarity_score": float(sources[0]["similarity_score"]) if sources else None,
            "fallback_triggered": metrics.get("fallback_triggered", False),
            "latency_ms": metrics.get("latency_ms", 0),
        }
        
        self.logger.info(json.dumps(log_payload))

analytics_logger = RAGAnalyticsLogger()

# Decorator to track latency of specific components
def track_latency(step_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = round((time.time() - start) * 1000, 2)
            logging.getLogger(__name__).debug(f"[LATENCY] {step_name}: {duration_ms}ms")
            return result
        return wrapper
    return decorator