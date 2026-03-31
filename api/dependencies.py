"""Dependency injection for FastAPI routes."""
from fastapi import HTTPException, status
from api.services.chatbot import chatbot_service
from api.services.cache import cache_service


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
