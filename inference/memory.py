from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SessionMemoryManager:
    """Manages multi-turn conversation context. (Ready to be backed by Redis)"""
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self._store: Dict[str, List[Dict[str, str]]] = {}

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self._store:
            self._store[session_id] = []
        
        self._store[session_id].append({"role": role, "content": content})
        
        if len(self._store[session_id]) > self.max_turns * 2: 
            self._store[session_id] = self._store[session_id][-(self.max_turns * 2):]

    def get_history_string(self, session_id: str) -> str:
        history = self._store.get(session_id,[])
        if not history:
            return "No prior conversation."
        
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])