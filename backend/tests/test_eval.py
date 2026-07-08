"""Eval harness + CI accuracy gate. Deterministic on the mock provider ($0)."""
from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient

from app.db.duckdb_manager import DuckDBManager
from app.db.session import SessionLocal
from app.repositories.eval import EvalRepository
from app.services.eval.cases import CASES
from app.services.eval.harness import run_suite
from app.services.sample_data.seed import seed_sample_data

# Regression floor for the deterministic pipeline. The suite includes deliberately
# hard cases the mock planner is expected to miss, so the ceiling is < 100% — that's
# the point. This floor catches regressions in the cases that should pass.
ACCURACY_FLOOR = 0.75


def test_eval_suite_meets_accuracy_gate() -> None:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        summary = asyncio.run(run_suite(s))

    assert summary.n_cases == len(CASES)
    assert summary.provider == "mock"
    assert summary.exec_accuracy >= ACCURACY_FLOOR, f"accuracy {summary.exec_accuracy:.0%}"
    assert summary.valid_sql_rate == 1.0
    # A suite that can't drop below 100% isn't measuring anything.
    assert summary.exec_accuracy < 1.0, "expected the hard cases to fail on the mock planner"


def test_eval_run_is_persisted_with_case_results() -> None:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())
        summary = asyncio.run(run_suite(s))
        repo = EvalRepository(s)
        run = repo.get_run(uuid.UUID(summary.run_id))
        assert run is not None and run.finished_at is not None and run.provider == "mock"
        cases = repo.case_results(run.id)
        assert len(cases) == len(CASES)
        passed = {c.case_id for c in cases if c.passed}
        failed = {c.case_id for c in cases if not c.passed}
        # Regression gate: every clear (non-hard) case must be answered correctly.
        clear_ids = {c.id for c in CASES if not c.hard}
        assert clear_ids <= passed, f"clear cases regressed: {clear_ids - passed}"
        # Meaningfulness: the deliberately-hard cases are expected to fail on mock.
        hard_ids = {c.id for c in CASES if c.hard}
        assert hard_ids <= failed


def test_eval_endpoints(client: TestClient) -> None:
    with SessionLocal() as s:
        seed_sample_data(s, DuckDBManager())

    run = client.post("/api/v1/eval/run")
    assert run.status_code == 200
    body = run.json()
    assert body["provider"] == "mock"
    assert body["exec_accuracy"] >= ACCURACY_FLOOR

    runs = client.get("/api/v1/eval/runs").json()
    assert len(runs) >= 1

    detail = client.get(f"/api/v1/eval/runs/{body['id']}").json()
    assert len(detail["cases"]) == len(CASES)
