"""Local-disk storage backend. pull/push are no-ops — the file is the source."""
from __future__ import annotations

from pathlib import Path


class LocalStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def local_path(self, key: str) -> Path:
        p = self._root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def pull(self, key: str) -> None:  # noqa: D401 - canonical location, nothing to fetch
        return None

    def push(self, key: str) -> None:
        return None

    def exists(self, key: str) -> bool:
        return (self._root / key).exists()

    def delete(self, key: str) -> None:
        p = self._root / key
        if p.exists():
            p.unlink()
