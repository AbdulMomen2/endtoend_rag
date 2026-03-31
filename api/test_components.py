#!/usr/bin/env python3
"""
Component test script to verify all services work correctly.
Run this before starting the API to ensure everything is configured properly.
"""
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        from api.config import api_config
        from api.services.cache import cache_service
        from api.services.chatbot import chatbot_service
        from api.models import ChatRequest, ChatResponse
        from api.routes import chat_router, health_router
        logger.info("✅ All imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def test_cache_service():
    """Test cache service (both Redis and in-memory)."""
    logger.info("\nTesting cache service...")
    try:
        from api.services.cache import CacheService
        
        cache = CacheService()
        
        # Test set/get
        test_key = "test:key:123"
        test_value = {"answer": "test", "timestamp": time.time()}
        
        cache.set(test_key, test_value, ttl=60)
        retrieved = cache.get(test_key)
        
        if retrieved and retrieved.get("answer") == "test":
            logger.info("✅ Cache set/get working")
        else:
            logger.warning("⚠️  Cache get returned unexpected value")
        
        # Test delete
        cache.delete(test_key)
        if cache.get(test_key) is None:
            logger.info("✅ Cache delete working")
        
        # Check Redis status
        if cache.is_redis_available():
            logger.info("✅ Redis is available and connected")
        else:
            logger.warning("⚠️  Redis not available, using in-memory cache")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache service test failed: {e}")
        return False


def test_chatbot_service():
    """Test chatbot service initialization."""
    logger.info("\nTesting chatbot service...")
    try:
        from api.services.chatbot import chatbot_service
        
        # Check if vector DB exists
        import os
        if not os.path.exists("vector_db/faiss_index"):
            logger.warning("⚠️  Vector DB not found. Run ingestion first:")
            logger.warning("   python3 -m ingestion.pipeline")
            return False
        
        # Initialize
        chatbot_service.initialize()
        
        if chatbot_service.is_ready():
            logger.info("✅ Chatbot service initialized successfully")
            
            # Test a simple query
            logger.info("Testing query processing...")
            response = chatbot_service.chat(
                session_id="test-session",
                user_query="What is this document about?",
                top_k=3
            )
            
            if "answer" in response:
                logger.info(f"✅ Query processed successfully")
                logger.info(f"   Answer length: {len(response['answer'])} chars")
                logger.info(f"   Sources: {len(response.get('sources', []))}")
            else:
                logger.warning("⚠️  Unexpected response format")
            
            return True
        else:
            logger.error("❌ Chatbot service not ready")
            return False
            
    except Exception as e:
        logger.error(f"❌ Chatbot service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test configuration loading."""
    logger.info("\nTesting configuration...")
    try:
        from api.config import api_config
        from core.config import config
        
        logger.info(f"  API Host: {api_config.HOST}:{api_config.PORT}")
        logger.info(f"  Redis: {'enabled' if api_config.REDIS_ENABLED else 'disabled'}")
        logger.info(f"  Cache: {'enabled' if api_config.CACHE_ENABLED else 'disabled'}")
        logger.info(f"  Rate limit: {api_config.RATE_LIMIT}")
        logger.info(f"  Embedding model: {config.EMBEDDING_MODEL}")
        logger.info(f"  Index path: {config.FAISS_INDEX_PATH}")
        
        logger.info("✅ Configuration loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False


def main():
    """Run all component tests."""
    logger.info("="*60)
    logger.info("RAG API Component Tests")
    logger.info("="*60)
    
    results = {
        "Imports": test_imports(),
        "Configuration": test_config(),
        "Cache Service": test_cache_service(),
        "Chatbot Service": test_chatbot_service(),
    }
    
    logger.info("\n" + "="*60)
    logger.info("Test Results Summary")
    logger.info("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    
    logger.info("="*60)
    if all_passed:
        logger.info("✅ All tests passed! API is ready to start.")
        logger.info("\nStart the API with:")
        logger.info("  python3 -m api.main")
        logger.info("  or")
        logger.info("  ./start_api.sh")
        return 0
    else:
        logger.error("❌ Some tests failed. Fix issues before starting API.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
