"""Project CRUD via the API."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

BASE = "/api/v1"


def test_create_list_get_delete(client: TestClient) -> None:
    r = client.post(f"{BASE}/projects", json={"name": "My Sales", "source": "duckdb"})
    assert r.status_code == 201, r.text
    project = r.json()
    assert project["slug"] == "my-sales"
    pid = project["id"]

    r = client.get(f"{BASE}/projects")
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    r = client.get(f"{BASE}/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "My Sales"

    r = client.delete(f"{BASE}/projects/{pid}")
    assert r.status_code == 204

    r = client.get(f"{BASE}/projects/{pid}")
    assert r.status_code == 404


def test_unknown_project_404(client: TestClient) -> None:
    r = client.get(f"{BASE}/projects/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_slug_collision_suffix(client: TestClient) -> None:
    a = client.post(f"{BASE}/projects", json={"name": "Dup", "source": "duckdb"}).json()
    b = client.post(f"{BASE}/projects", json={"name": "Dup", "source": "duckdb"}).json()
    assert a["slug"] == "dup"
    assert b["slug"] == "dup-2"
