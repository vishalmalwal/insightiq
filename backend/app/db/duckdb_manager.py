"""One DuckDB database file per project (analytics store).

Files live behind a StorageBackend (local disk, or R2 for deploy) so the app is
portable across hosts with ephemeral disks. Read-heavy, connection-per-request.
Postgres-connector queries run read-only via psycopg with a dedicated role +
statement timeout (Phase 1).
"""
from __future__ import annotations

import duckdb

from app.services.storage import get_storage_backend
from app.services.storage.base import StorageBackend


class DuckDBManager:
    def __init__(self, storage: StorageBackend | None = None) -> None:
        self._storage = storage or get_storage_backend()

    def _key(self, project_id: str) -> str:
        return f"duckdb/{project_id}.duckdb"

    def connect(self, project_id: str, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        key = self._key(project_id)
        self._storage.pull(key)  # no-op for local; downloads for R2
        path = self._storage.local_path(key)
        if read_only and not path.exists():
            raise FileNotFoundError(f"No DuckDB store for project {project_id}")
        return duckdb.connect(str(path), read_only=read_only)

    def persist(self, project_id: str) -> None:
        """Upload the project's DuckDB file to the backend (no-op for local)."""
        self._storage.push(self._key(project_id))

    def exists(self, project_id: str) -> bool:
        return self._storage.exists(self._key(project_id))

    def delete(self, project_id: str) -> None:
        self._storage.delete(self._key(project_id))
