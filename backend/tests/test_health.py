"""Smoke tests for the Phase 0 scaffold."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_api_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_system_info(client: TestClient) -> None:
    resp = client.get("/api/v1/system/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app_name"] == "InsightIQ"
    assert "planner_model" in body


def test_request_id_header(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.headers.get("x-request-id")
