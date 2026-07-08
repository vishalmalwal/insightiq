"""PATCH /dashboards/{id} persists a user-adjusted grid layout."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.duckdb_manager import DuckDBManager
from app.db.session import SessionLocal
from app.repositories.projects import ProjectRepository
from app.services.sample_data.seed import seed_sample_data

BASE = "/api/v1"


def test_patch_layout_roundtrip(client: TestClient) -> None:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        pid = str(ProjectRepository(s).get_by_slug("sample-ecommerce").id)

    ask = client.post(f"{BASE}/projects/{pid}/ask", json={"question": "revenue by region"}).json()
    dash_id = ask["dashboard_id"]
    assert dash_id

    layout = [{"i": "i1", "x": 0, "y": 0, "w": 6, "h": 4}]
    patched = client.patch(f"{BASE}/dashboards/{dash_id}", json={"layout": layout})
    assert patched.status_code == 200
    assert patched.json()["layout"] == layout

    # Reloading the shared dashboard returns the saved layout.
    reloaded = client.get(f"{BASE}/dashboards/{dash_id}").json()
    assert reloaded["layout"] == layout


def test_patch_missing_dashboard_404(client: TestClient) -> None:
    r = client.patch(
        f"{BASE}/dashboards/00000000-0000-0000-0000-000000000000", json={"layout": []}
    )
    assert r.status_code == 404
