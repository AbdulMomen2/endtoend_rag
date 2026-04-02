"""
Session memory manager with Redis backend and in-memory fallback.
Redis gives persistence across restarts and shared state across workers.
"""
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

SESSION_TTL = 86400  # 24 hours
SESSION_PREFIX = "rag:session:"


class SessionMemoryManager:
    """
    Multi-turn conversation memory.
    Uses Redis when available, falls back to in-memory dict.
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._store: Dict[str, List[Dict[str, str]]] = {}  # fallback
        self._redis = None
        self._try_connect_redis()

    def _try_connect_redis(self):
        try:
            import redis
            from core.config import config
            # Read Redis config from env via core config
            import os
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            self._redis = redis.Redis(
                host=host, port=port, db=1,  # db=1 to separate from cache (db=0)
                socket_timeout=3,
                socket_connect_timeout=3,
                decode_responses=True
            )
            self._redis.ping()
            logger.info("SessionMemoryManager: Redis connected.")
        except Exception as e:
            logger.warning(f"SessionMemoryManager: Redis unavailable, using in-memory. ({e})")
            self._redis = None

    def _key(self, session_id: str) -> str:
        return f"{SESSION_PREFIX}{session_id}"

    def _get_messages(self, session_id: str) -> List[Dict[str, str]]:
        if self._redis:
            try:
                raw = self._redis.get(self._key(session_id))
                return json.loads(raw) if raw else []
            except Exception:
                pass
        return self._store.get(session_id, [])

    def _set_messages(self, session_id: str, messages: List[Dict[str, str]]):
        if self._redis:
            try:
                self._redis.setex(
                    self._key(session_id),
                    SESSION_TTL,
                    json.dumps(messages)
                )
                return
            except Exception:
                pass
        self._store[session_id] = messages

    def add_message(self, session_id: str, role: str, content: str):
        messages = self._get_messages(session_id)
        messages.append({"role": role, "content": content})
        # Keep only last max_turns * 2 messages
        if len(messages) > self.max_turns * 2:
            messages = messages[-(self.max_turns * 2):]
        self._set_messages(session_id, messages)

    def get_history_string(self, session_id: str) -> str:
        messages = self._get_messages(session_id)
        if not messages:
            return "No prior conversation."
        return "\n".join(
            [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
        )

    def clear_session(self, session_id: str):
        if self._redis:
            try:
                self._redis.delete(self._key(session_id))
            except Exception:
                pass
        self._store.pop(session_id, None)
