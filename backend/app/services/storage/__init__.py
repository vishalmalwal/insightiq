"""Storage backend factory."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.storage.base import StorageBackend


def get_storage_backend() -> StorageBackend:
    s = get_settings()
    if s.storage_backend == "r2":
        from app.services.storage.r2 import R2Storage

        missing = [
            k
            for k, v in {
                "r2_account_id": s.r2_account_id,
                "r2_access_key_id": s.r2_access_key_id,
                "r2_secret_access_key": s.r2_secret_access_key,
                "r2_bucket": s.r2_bucket,
            }.items()
            if not v
        ]
        if missing:
            raise RuntimeError(f"R2 backend selected but missing config: {missing}")
        return R2Storage(
            account_id=s.r2_account_id,  # type: ignore[arg-type]
            access_key_id=s.r2_access_key_id,  # type: ignore[arg-type]
            secret_access_key=s.r2_secret_access_key,  # type: ignore[arg-type]
            bucket=s.r2_bucket,  # type: ignore[arg-type]
            cache_dir=s.duckdb_dir,
        )
    from app.services.storage.local import LocalStorage

    return LocalStorage(s.duckdb_dir)
