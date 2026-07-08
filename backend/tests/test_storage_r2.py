"""R2 backend logic, exercised with a fake S3 client (no network)."""
from __future__ import annotations

from pathlib import Path

from app.services.storage.r2 import R2Storage


class _NotFoundError(Exception):
    def __init__(self) -> None:
        self.response = {"Error": {"Code": "NoSuchKey"}}


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def download_file(self, bucket: str, key: str, dest: str) -> None:
        if key not in self.objects:
            raise _NotFoundError()
        Path(dest).write_bytes(self.objects[key])

    def upload_file(self, src: str, bucket: str, key: str) -> None:
        self.objects[key] = Path(src).read_bytes()

    def head_object(self, Bucket: str, Key: str) -> None:  # noqa: N803
        if Key not in self.objects:
            raise _NotFoundError()

    def delete_object(self, Bucket: str, Key: str) -> None:  # noqa: N803
        self.objects.pop(Key, None)


def _backend(tmp_path: Path) -> tuple[R2Storage, FakeS3]:
    s = R2Storage(
        account_id="acct", access_key_id="k", secret_access_key="s",
        bucket="b", cache_dir=str(tmp_path),
    )
    fake = FakeS3()
    s._client = fake
    return s, fake


def test_push_then_exists_and_pull_roundtrip(tmp_path) -> None:
    s, fake = _backend(tmp_path)
    key = "projects/p1.duckdb"
    s.local_path(key).write_bytes(b"duckdb-bytes")
    s.push(key)
    assert key in fake.objects

    # Fresh instance (empty cache) pulls the object down.
    s2, _ = _backend(tmp_path / "other")
    s2._client = fake
    assert s2.exists(key) is True
    s2.pull(key)
    assert s2.local_path(key).read_bytes() == b"duckdb-bytes"


def test_pull_missing_is_tolerated(tmp_path) -> None:
    s, _ = _backend(tmp_path)
    s.pull("projects/does-not-exist.duckdb")  # no error; file simply absent
    assert not s.local_path("projects/does-not-exist.duckdb").exists()


def test_exists_false_and_delete(tmp_path) -> None:
    s, fake = _backend(tmp_path)
    assert s.exists("projects/none.duckdb") is False
    key = "projects/p2.duckdb"
    s.local_path(key).write_bytes(b"x")
    s.push(key)
    s.delete(key)
    assert key not in fake.objects
    assert not s.local_path(key).exists()
