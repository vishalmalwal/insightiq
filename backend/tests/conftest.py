"""Test fixtures. SQLite metadata DB + temp DuckDB dir + mock LLM → no server, no cost.

Env is set at import time (before any app import) so the settings/engine pick it up.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="insightiq_test_")
os.environ["ENVIRONMENT"] = "ci"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/meta.db"
os.environ["DUCKDB_DIR"] = f"{_TMP}/duckdb"

from cryptography.fernet import Fernet  # noqa: E402

os.environ["CREDENTIALS_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _schema():
    """Fresh schema + clean DuckDB store around every test."""
    from app.db.session import create_all, drop_all

    create_all()
    yield
    drop_all()
    duck = Path(os.environ["DUCKDB_DIR"])
    if duck.exists():
        shutil.rmtree(duck, ignore_errors=True)


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def db_session():
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
