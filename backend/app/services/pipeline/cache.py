"""Response cache keyed on hash(question + semantic-layer version).

Repeated demo traffic returns instantly and never re-hits the LLM quota.
Backed by the `query_cache` table (can move to Redis with a TTL in Phase 6).
"""
from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.db.models import QueryCache


class ResponseCache:
    def __init__(self, session: Session) -> None:
        self._s = session

    @staticmethod
    def key(
        project_id: uuid.UUID,
        sem_version: int,
        question: str,
        date_range: tuple[str, str] | None = None,
    ) -> str:
        dr = f"{date_range[0]}:{date_range[1]}" if date_range else ""
        raw = f"{project_id}:{sem_version}:{question.strip().lower()}:{dr}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        row = self._s.get(QueryCache, key)
        return dict(row.response) if row else None

    def set(self, key: str, project_id: uuid.UUID, response: dict) -> None:
        row = self._s.get(QueryCache, key)
        if row:
            row.response = response
        else:
            self._s.add(QueryCache(key_hash=key, project_id=project_id, response=response))
        self._s.flush()
