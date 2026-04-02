import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

JOB_PREFIX = "rag:job:"
JOB_TTL = 3600


class JobStore:
    def __init__(self):
        self._store: Dict[str, Dict] = {}
        self._redis = None
        self._try_redis()

    
    def _try_redis(self):
        try:
            import redis, os
            self._redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=2, decode_responses=True,
                socket_timeout=3, socket_connect_timeout=3
            )
            self._redis.ping()
        except Exception:
            self._redis = None

    
    def create(self, job_id: str, filename: str):
        data = {"job_id": job_id, "filename": filename, "status": "queued",
                "created_at": time.time(), "result": None, "error": None}
        self._write(job_id, data)

    
    def update(self, job_id: str, **kwargs):
        data = self._read(job_id) or {}
        data.update(kwargs)
        self._write(job_id, data)

    
    def get(self, job_id: str) -> Optional[Dict]:
        return self._read(job_id)

    
    def _write(self, job_id: str, data: Dict):
        if self._redis:
            try:
                self._redis.setex(f"{JOB_PREFIX}{job_id}", JOB_TTL, json.dumps(data))
                return
            except Exception:
                pass
        self._store[job_id] = data

    
    def _read(self, job_id: str) -> Optional[Dict]:
        if self._redis:
            try:
                raw = self._redis.get(f"{JOB_PREFIX}{job_id}")
                return json.loads(raw) if raw else None
            except Exception:
                pass
        return self._store.get(job_id)


job_store = JobStore()
