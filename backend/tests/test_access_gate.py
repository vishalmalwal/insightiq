"""When a shared secret is configured, mutating routes require the header."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings

BASE = "/api/v1"


def test_gate_blocks_without_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "app_shared_secret", "topsecret")

    # Missing header → 401
    r = client.post(f"{BASE}/projects", json={"name": "Gated", "source": "duckdb"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"

    # Correct header → allowed
    r = client.post(
        f"{BASE}/projects",
        json={"name": "Gated", "source": "duckdb"},
        headers={"x-app-secret": "topsecret"},
    )
    assert r.status_code == 201

    # Read-only browsing stays open even while gated
    assert client.get(f"{BASE}/projects").status_code == 200
