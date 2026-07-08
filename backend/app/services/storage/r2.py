"""Cloudflare R2 (S3-compatible) storage backend for per-project DuckDB files.

R2 gives 10 GB + zero egress on the free tier. Objects are cached locally under
`cache_dir`: `pull` downloads on demand (skipped if already cached), `push`
uploads after a write. Missing objects are tolerated so a first-time ingest can
create the file locally and then push it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_NOT_FOUND = {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}


class R2Storage:
    def __init__(
        self,
        *,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        cache_dir: str,
    ) -> None:
        self._bucket = bucket
        self._cache = Path(cache_dir)
        self._cache.mkdir(parents=True, exist_ok=True)
        self._endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        self._creds = (access_key_id, secret_access_key)
        self._client: Any = None

    def _s3(self) -> Any:
        if self._client is None:
            import boto3  # lazy import so local dev needs no boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._creds[0],
                aws_secret_access_key=self._creds[1],
                region_name="auto",
            )
        return self._client

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        return code in _NOT_FOUND

    def local_path(self, key: str) -> Path:
        p = self._cache / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def pull(self, key: str) -> None:
        path = self.local_path(key)
        if path.exists():
            return  # cached — load-on-demand, download once
        try:
            self._s3().download_file(self._bucket, key, str(path))
        except Exception as exc:  # noqa: BLE001
            if self._is_not_found(exc):
                return  # not uploaded yet; a write will create it locally
            raise

    def push(self, key: str) -> None:
        path = self.local_path(key)
        if path.exists():
            self._s3().upload_file(str(path), self._bucket, key)

    def exists(self, key: str) -> bool:
        if self.local_path(key).exists():
            return True
        try:
            self._s3().head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception as exc:  # noqa: BLE001
            if self._is_not_found(exc):
                return False
            raise

    def delete(self, key: str) -> None:
        path = self.local_path(key)
        if path.exists():
            path.unlink()
        try:
            self._s3().delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            if not self._is_not_found(exc):
                raise
