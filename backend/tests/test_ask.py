"""End-to-end ask endpoint, plus self-correction and graceful degradation."""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.db.duckdb_manager import DuckDBManager
from app.db.session import SessionLocal
from app.repositories.projects import ProjectRepository
from app.repositories.semantic_layers import SemanticLayerRepository
from app.schemas.pipeline import AnalysisIntent
from app.schemas.semantic_layer import SemanticLayerSpec
from app.services.llm.errors import RateLimitError
from app.services.pipeline.orchestrator import AskOrchestrator
from app.services.sample_data.seed import seed_sample_data

BASE = "/api/v1"
FLAGSHIP = "compare monthly revenue by region this year vs last year and show top products"


def _seed_ecom() -> str:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        return str(ProjectRepository(s).get_by_slug("sample-ecommerce").id)


def test_ask_returns_plan_and_result_cards(client: TestClient) -> None:
    pid = _seed_ecom()
    r = client.post(f"{BASE}/projects/{pid}/ask", json={"question": FLAGSHIP})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["degraded"] is False
    assert len(body["plan"]["intents"]) >= 1
    ok_cards = [c for c in body["cards"] if c["ok"]]
    assert ok_cards, body["cards"]
    # A revenue-by-region card must have used the event date, never signup_date.
    comparison = next((c for c in ok_cards if c["type"] == "comparison"), None)
    if comparison:
        assert "order_date" in comparison["sql"].lower()
        assert "signup_date" not in comparison["sql"].lower()


def test_ask_is_cached_on_second_call(client: TestClient) -> None:
    pid = _seed_ecom()
    first = client.post(f"{BASE}/projects/{pid}/ask", json={"question": "revenue by region"})
    assert first.json()["cache_hit"] is False
    second = client.post(f"{BASE}/projects/{pid}/ask", json={"question": "revenue by region"})
    assert second.json()["cache_hit"] is True


def test_ask_degrades_gracefully_on_rate_limit(client: TestClient, monkeypatch) -> None:
    pid = _seed_ecom()

    async def boom(self, question, sem):  # noqa: ANN001
        raise RateLimitError("quota exceeded")

    monkeypatch.setattr("app.services.pipeline.planner.Planner.plan", boom)
    r = client.post(f"{BASE}/projects/{pid}/ask", json={"question": "anything"})
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert body["message"]
    assert body["cards"] == []


def _sem_for(session, project_id) -> SemanticLayerSpec:
    row = SemanticLayerRepository(session).get_active(project_id)
    return SemanticLayerSpec.model_validate(row.spec)


def test_self_correction_retries_then_succeeds() -> None:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        ecom = ProjectRepository(s).get_by_slug("sample-ecommerce")
        sem = _sem_for(s, ecom.id)
        orch = AskOrchestrator(s)
        orch._can_repair = True  # simulate an LLM able to repair

        calls = {"n": 0}

        async def fake_gen(intent, sem_, dialect, error, prev_sql, date_range=None):  # noqa: ANN001
            calls["n"] += 1
            if calls["n"] == 1:
                return "SELECT nonexistent_col FROM orders"      # fails on execute
            return "SELECT status, COUNT(*) AS c FROM orders GROUP BY status"

        orch._generate_sql = fake_gen  # type: ignore[assignment]
        intent = AnalysisIntent(id="i1", type="breakdown", title="t", entity="orders")
        card = asyncio.run(orch._run_intent(ecom.id, intent, sem, "duckdb"))
        assert card.ok is True
        assert calls["n"] == 2  # one retry


def test_permanent_failure_produces_degraded_card() -> None:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        ecom = ProjectRepository(s).get_by_slug("sample-ecommerce")
        sem = _sem_for(s, ecom.id)
        orch = AskOrchestrator(s)
        orch._can_repair = True

        async def always_bad(intent, sem_, dialect, error, prev_sql, date_range=None):  # noqa: ANN001
            return "SELECT nonexistent_col FROM orders"

        orch._generate_sql = always_bad  # type: ignore[assignment]
        intent = AnalysisIntent(id="i1", type="kpi", title="t", entity="orders")
        card = asyncio.run(orch._run_intent(ecom.id, intent, sem, "duckdb"))
        assert card.ok is False
        assert card.error
