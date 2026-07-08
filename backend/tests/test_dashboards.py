"""Phase 4 backend: date filter, distribution, captions, persistence, sample Qs."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.duckdb_manager import DuckDBManager
from app.db.session import SessionLocal
from app.repositories.projects import ProjectRepository
from app.services.sample_data.seed import seed_sample_data

BASE = "/api/v1"


def _ask(client, pid, question, **kw):
    return client.post(f"{BASE}/projects/{pid}/ask", json={"question": question, **kw}).json()


def _seed() -> tuple[str, str]:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        return (
            str(ProjectRepository(s).get_by_slug("sample-ecommerce").id),
            str(ProjectRepository(s).get_by_slug("sample-saas").id),
        )


def test_sample_questions_endpoint(client: TestClient) -> None:
    ecom, saas = _seed()
    qs = client.get(f"{BASE}/projects/{ecom}/sample-questions").json()
    assert len(qs) == 4 and all(isinstance(q, str) for q in qs)
    assert len(client.get(f"{BASE}/projects/{saas}/sample-questions").json()) == 4


def test_distribution_question_produces_donut_shape(client: TestClient) -> None:
    ecom, _ = _seed()
    body = _ask(client, ecom, "revenue share by region")
    card = body["cards"][0]
    assert card["type"] == "distribution"
    assert card["ok"] and card["row_count"] <= 6  # few categories → donut on the client


def test_date_filter_reduces_rows_and_caches_separately(client: TestClient) -> None:
    ecom, _ = _seed()
    full = _ask(client, ecom, "monthly revenue trend")
    filtered = _ask(
        client, ecom, "monthly revenue trend", date_from="2025-01-01", date_to="2025-12-31"
    )
    assert filtered["cards"][0]["row_count"] < full["cards"][0]["row_count"]
    assert "between" in filtered["cards"][0]["sql"].lower()
    assert filtered["cache_hit"] is False  # different key than the unfiltered query


def test_captions_skipped_on_mock_provider(client: TestClient) -> None:
    ecom, _ = _seed()
    body = _ask(client, ecom, "top categories by revenue")
    assert all(c["caption"] is None for c in body["cards"])  # mock → no captions


def test_dashboard_is_persisted_and_reloadable(client: TestClient) -> None:
    ecom, _ = _seed()
    body = _ask(client, ecom, "monthly revenue trend")
    dash_id = body["dashboard_id"]
    assert dash_id

    reload = client.get(f"{BASE}/dashboards/{dash_id}")
    assert reload.status_code == 200
    payload = reload.json()
    assert payload["response"]["question"] == "monthly revenue trend"
    assert payload["response"]["cards"][0]["ok"]

    listed = client.get(f"{BASE}/projects/{ecom}/dashboards").json()
    assert any(d["id"] == dash_id for d in listed)


def test_unknown_dashboard_is_404(client: TestClient) -> None:
    _seed()
    r = client.get(f"{BASE}/dashboards/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
