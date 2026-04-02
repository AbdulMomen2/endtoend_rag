"""Dependency injection for FastAPI routes."""
from fastapi import HTTPException, status, Security
from fastapi.security import APIKeyHeader
from api.services.chatbot import chatbot_service
from api.services.cache import cache_service
from api.config import api_config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)):
    """
    Optional API key auth. If API_KEY is set in config, all requests must include
    the X-API-Key header. If not set, auth is disabled (open access).
    """
    if api_config.API_KEY:
        if not api_key or api_key != api_config.API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key. Include X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )


def get_chatbot_service():
    """Dependency to inject chatbot service."""
    if not chatbot_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service initializing, please retry in a few seconds"
        )
    return chatbot_service


def get_cache_service():
    """Dependency to inject cache service."""
    return cache_service
