"""Health check and metrics endpoints."""
import time
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from api.models.responses import HealthResponse, MetricsResponse
from api.services.chatbot import chatbot_service
from api.services.cache import cache_service
from api.dependencies import get_cache_service
from core.metrics import generate_latest, CONTENT_TYPE_LATEST, METRICS_ENABLED

router = APIRouter(tags=["System"])

# Store startup time
_startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(cache: cache_service = Depends(get_cache_service)):
    """
    Health check endpoint for load balancers and monitoring.
    Returns service status and component health.
    """
    return HealthResponse(
        status="healthy" if chatbot_service.is_ready() else "initializing",
        version="2.0.0",
        index_loaded=chatbot_service.is_ready(),
        redis_connected=cache.is_redis_available(),
        timestamp=time.time()
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(cache: cache_service = Depends(get_cache_service)):
    """
    Basic metrics endpoint for monitoring.
    Can be extended to export Prometheus metrics.
    """
    return MetricsResponse(
        cache_size=cache.get_size(),
        uptime_seconds=time.time() - _startup_time,
        redis_enabled=cache.is_redis_available()
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe.
    Returns 200 only when service is ready to accept traffic.
    """
    if not chatbot_service.is_ready():
        return {"ready": False}, 503
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"alive": True}


@router.get("/metrics/prometheus", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
