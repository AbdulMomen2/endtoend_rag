"""API-specific configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class APIConfig(BaseSettings):
    """API configuration with environment variable support."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False
    
    # Security
    RATE_LIMIT: str = "30/minute"
    MAX_QUERY_LENGTH: int = 500
    MIN_QUERY_LENGTH: int = 1
    ALLOWED_ORIGINS: list = ["*"]
    API_KEY: str = ""  # Set to require X-API-Key header on all endpoints
    
    # Cache
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 100
    
    # Redis
    REDIS_ENABLED: bool = True
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    
    # Retrieval
    DEFAULT_TOP_K: int = 3
    MAX_TOP_K: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore keys like OPENAI_API_KEY defined in .env for other modules


api_config = APIConfig()
