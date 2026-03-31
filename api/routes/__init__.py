"""API routes."""
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router

__all__ = ["chat_router", "health_router", "ingest_router"]
