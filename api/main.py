"""
Production-ready FastAPI application for RAG chatbot.
Organized structure with proper separation of concerns.
"""
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.config import api_config
from api.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware
from api.routes import chat_router, health_router, ingest_router
from api.services.chatbot import chatbot_service
from api.services.cache import cache_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, api_config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting RAG API server...")
    logger.info(f"   Redis: {'enabled' if api_config.REDIS_ENABLED else 'disabled'}")
    logger.info(f"   Cache: {'enabled' if api_config.CACHE_ENABLED else 'disabled'}")
    logger.info(f"   Rate limit: {api_config.RATE_LIMIT}")
    
    try:
        # Initialize chatbot
        chatbot_service.initialize()
        
        # Test cache
        if cache_service.is_redis_available():
            logger.info("✅ Redis cache is available")
        else:
            logger.warning("⚠️  Using in-memory cache (Redis unavailable)")
        
        logger.info("✅ RAG API server ready")
        
    except Exception as e:
        logger.critical(f"❌ Startup failed: {e}")
        raise RuntimeError(f"Failed to start server: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down RAG API server...")
    chatbot_service.shutdown()
    cache_service.clear_all()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Enterprise RAG API",
    description="Production-grade document Q&A with hybrid retrieval and guardrails",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add rate limiter
from api.routes.chat import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware (order matters - first added = outermost)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Trusted host protection
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # TODO: Restrict in production
)

# Include routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(ingest_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Enterprise RAG API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=api_config.HOST,
        port=api_config.PORT,
        reload=api_config.RELOAD,
        workers=api_config.WORKERS,
        log_level=api_config.LOG_LEVEL.lower()
    )
