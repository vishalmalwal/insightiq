"""Pluggable storage backend for per-project DuckDB files.

Develop against local disk; flip a config flag to Cloudflare R2 (S3-compatible)
for deploy. Load-on-demand + local cache keeps hosts with ephemeral disks happy
without pinning a volume.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def local_path(self, key: str) -> Path:
        """Local working path for `key` (parent dirs created). Canonical location
        for the Local backend; cache location for remote backends."""
        ...

    def pull(self, key: str) -> None:
        """Ensure the object is present at `local_path(key)` (download if remote)."""
        ...

    def push(self, key: str) -> None:
        """Persist the local file at `local_path(key)` to the backend (upload if remote)."""
        ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...
