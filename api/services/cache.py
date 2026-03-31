"""Redis-backed cache service with fallback to in-memory."""
import json
import hashlib
import time
import logging
from typing import Optional, Dict, Any

from api.config import api_config

logger = logging.getLogger(__name__)


class CacheService:
    """
    Cache service with Redis primary and in-memory fallback.
    Thread-safe and production-ready.
    """
    
    def __init__(self):
        self.redis_client: Optional[Any] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.redis_available = False
        
        if api_config.REDIS_ENABLED:
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection with error handling."""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=api_config.REDIS_HOST,
                port=api_config.REDIS_PORT,
                db=api_config.REDIS_DB,
                password=api_config.REDIS_PASSWORD,
                socket_timeout=api_config.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=api_config.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("✅ Redis cache connected successfully")
        except ImportError:
            logger.warning("⚠️  redis-py not installed, using in-memory cache")
            self.redis_available = False
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}. Using in-memory cache")
            self.redis_available = False
    
    def get_cache_key(self, session_id: str, query: str) -> str:
        """Generate deterministic cache key."""
        content = f"{session_id}:{query}".encode('utf-8')
        return f"rag:cache:{hashlib.sha256(content).hexdigest()}"
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get value from cache (Redis first, then memory).
        Returns None if not found or expired.
        """
        # Try Redis first
        if self.redis_available and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    logger.debug(f"Redis cache hit: {key}")
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                self.redis_available = False
        
        # Fallback to memory cache
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if time.time() - entry["timestamp"] < api_config.CACHE_TTL:
                logger.debug(f"Memory cache hit: {key}")
                return entry["value"]
            else:
                # Expired
                del self.memory_cache[key]
        
        return None
    
    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set value in cache (both Redis and memory for redundancy).
        Returns True if successful.
        """
        if ttl is None:
            ttl = api_config.CACHE_TTL
        
        success = False
        
        # Try Redis first
        if self.redis_available and self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
                success = True
                logger.debug(f"Redis cache set: {key}")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                self.redis_available = False
        
        # Always set in memory as backup
        self.memory_cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        
        # Simple LRU eviction for memory cache
        if len(self.memory_cache) > api_config.CACHE_MAX_SIZE:
            oldest_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k]["timestamp"]
            )
            del self.memory_cache[oldest_key]
            logger.debug(f"Memory cache evicted: {oldest_key}")
        
        return success or len(self.memory_cache) > 0
    
    def delete(self, key: str) -> bool:
        """Delete key from both Redis and memory cache."""
        success = False
        
        if self.redis_available and self.redis_client:
            try:
                self.redis_client.delete(key)
                success = True
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        if key in self.memory_cache:
            del self.memory_cache[key]
            success = True
        
        return success
    
    def clear_session(self, session_id: str) -> int:
        """Clear all cache entries for a session. Returns count of deleted keys."""
        pattern = f"rag:cache:*{session_id}*"
        deleted = 0
        
        # Clear from Redis
        if self.redis_available and self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted += self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear session error: {e}")
        
        # Clear from memory
        keys_to_delete = [
            k for k in self.memory_cache.keys()
            if session_id in k
        ]
        for key in keys_to_delete:
            del self.memory_cache[key]
            deleted += 1
        
        return deleted
    
    def get_size(self) -> int:
        """Get current cache size (memory only, Redis size requires DBSIZE)."""
        return len(self.memory_cache)
    
    def is_redis_available(self) -> bool:
        """Check if Redis is currently available."""
        if not self.redis_available or not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            self.redis_available = False
            return False
    
    def clear_all(self):
        """Clear all cache entries (use with caution)."""
        if self.redis_available and self.redis_client:
            try:
                # Only clear keys with our prefix
                keys = self.redis_client.keys("rag:cache:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear all error: {e}")
        
        self.memory_cache.clear()


# Global cache instance
cache_service = CacheService()
