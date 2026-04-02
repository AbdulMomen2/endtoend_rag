"""Chatbot service wrapper."""
import logging
from typing import Optional, Dict, Any
from inference.pipeline import ChatbotPipeline

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Singleton wrapper for ChatbotPipeline.
    Handles initialization and provides a clean interface.
    """
    
    _instance: Optional['ChatbotService'] = None
    _pipeline: Optional[ChatbotPipeline] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Initialize the chatbot pipeline (called once at startup)."""
        
        if self._pipeline is None:
            logger.info("Initializing ChatbotPipeline...")
            try:
                self._pipeline = ChatbotPipeline()
                logger.info("ChatbotPipeline initialized successfully")
            except Exception as e:
                logger.critical(f" Failed to initialize ChatbotPipeline: {e}")
                raise RuntimeError(f"Chatbot initialization failed: {e}")
    
    def is_ready(self) -> bool:
        """Check if chatbot is ready to serve requests."""
        return self._pipeline is not None

    @property
    def pipeline(self) -> ChatbotPipeline:
        """Direct access to pipeline for streaming."""

        if not self._pipeline:
            raise RuntimeError("Chatbot not initialized")
        return self._pipeline
    
    def chat(self, session_id: str, user_query: str, top_k: int = 3,
             doc_id: str = None, provider: str = None, model: str = None) -> Dict[str, Any]:
        if not self.is_ready():
            raise RuntimeError("Chatbot not initialized")
        # If a different model is requested, swap the generator on the fly
        if provider and model:
            current = self._pipeline.generator
            if current.provider != provider or current.model != model:
                from inference.generator import GroundedGenerator
                self._pipeline.generator = GroundedGenerator(provider=provider, model=model)
        return self._pipeline.chat(
            session_id=session_id,
            user_query=user_query,
            top_k=top_k,
            doc_id=doc_id
        )

    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session to clear
            
        Returns:
            True if successful
        """

        if not self.is_ready():
            return False
        
        try:
            if session_id in self._pipeline.memory._store:
                del self._pipeline.memory._store[session_id]
                return True
            return False

        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {e}")
            return False
    
    def shutdown(self):
        """Cleanup resources on shutdown."""

        if self._pipeline:
            logger.info("Shutting down ChatbotPipeline...")
            self._pipeline = None


chatbot_service = ChatbotService()
