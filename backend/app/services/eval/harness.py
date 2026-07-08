"""Run the eval suite: per case, ask the pipeline and compare its result set to the
gold query's (denotation match). Computes execution accuracy, valid-SQL rate, and
intent accuracy, and persists an EvalRun + per-case results.
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.duckdb_manager import DuckDBManager
from app.repositories.eval import EvalRepository
from app.repositories.projects import ProjectRepository
from app.services.eval.cases import CASES, SUITE_VERSION, EvalCase
from app.services.pipeline.executor import DuckDBExecutor
from app.services.pipeline.orchestrator import AskOrchestrator

log = get_logger("insightiq.eval")


@dataclass
class EvalSummary:
    run_id: str
    suite_version: str
    provider: str
    n_cases: int
    exec_accuracy: float
    valid_sql_rate: float
    intent_accuracy: float
    avg_latency_ms: float
    total_cost_usd: float


def _denote(rows: list[list[object]]) -> Counter:
    """Order- and column-order-insensitive fingerprint of a result set."""

    def norm(v: object) -> str:
        if isinstance(v, float):
            return str(round(v, 2))
        return str(v)

    # Narrow limitation: collapsing a row into a frozenset of its values is
    # column-order-insensitive, but a row whose measure value equals one of its
    # labels (e.g. count 4 in a row also containing the string "4") could blur.
    return Counter(frozenset(norm(v) for v in row) for row in rows)


async def run_suite(session: Session, git_sha: str | None = None) -> EvalSummary:
    from app.core.config import get_settings

    provider = get_settings().llm_provider
    duck = DuckDBManager()
    executor = DuckDBExecutor(duck)
    projects = ProjectRepository(session)
    repo = EvalRepository(session)
    run = repo.create_run(SUITE_VERSION, provider, git_sha)

    matched_n = valid_n = intent_n = 0
    total_latency = total_cost = 0.0

    for case in CASES:
        result = await _run_case(session, duck, executor, projects, case)
        repo.add_case_result(
            run.id,
            case.id,
            passed=result["matched"],
            generated_sql=result["sql"],
            error=result["error"],
            latency_ms=result["latency_ms"],
            cost_usd=result["cost_usd"],
        )
        matched_n += result["matched"]
        valid_n += result["valid"]
        intent_n += result["intent_ok"]
        total_latency += result["latency_ms"]
        total_cost += result["cost_usd"]
        log.info("eval_case", case=case.id, matched=result["matched"], valid=result["valid"])

    n = len(CASES)
    repo.finalize_run(
        run,
        exec_accuracy=matched_n / n,
        valid_sql_rate=valid_n / n,
        intent_accuracy=intent_n / n,
        avg_latency_ms=total_latency / n,
        total_cost_usd=total_cost,
    )
    session.commit()
    return EvalSummary(
        run_id=str(run.id),
        suite_version=SUITE_VERSION,
        provider=provider,
        n_cases=n,
        exec_accuracy=matched_n / n,
        valid_sql_rate=valid_n / n,
        intent_accuracy=intent_n / n,
        avg_latency_ms=total_latency / n,
        total_cost_usd=total_cost,
    )


async def _run_case(
    session: Session,
    duck: DuckDBManager,
    executor: DuckDBExecutor,
    projects: ProjectRepository,
    case: EvalCase,
) -> dict:
    project = projects.get_by_slug(case.project_slug)
    if project is None:
        return {
            "matched": False, "valid": False, "intent_ok": False,
            "sql": None, "error": f"project {case.project_slug} not seeded",
            "latency_ms": 0.0, "cost_usd": 0.0,
        }

    orch = AskOrchestrator(session, duck)
    t0 = time.perf_counter()
    try:
        resp = await orch.ask(project, case.question)
    except Exception as exc:  # noqa: BLE001 - provider/API failure → record, don't crash
        return {
            "matched": False, "valid": False, "intent_ok": False, "sql": None,
            "error": str(exc)[:200], "latency_ms": (time.perf_counter() - t0) * 1000,
            "cost_usd": 0.0,
        }
    latency_ms = (time.perf_counter() - t0) * 1000
    ok_cards = [c for c in resp.cards if c.ok]
    valid = all(c.ok for c in resp.cards)  # no card produced invalid/failed SQL

    # Unanswerable questions: the correct behaviour is to NOT fabricate an answer.
    if case.expect_no_answer:
        matched = len(ok_cards) == 0
        return {
            "matched": matched, "valid": valid, "intent_ok": True,
            "sql": (resp.cards[0].sql if resp.cards else None),
            "error": None if matched else "fabricated an answer for an unanswerable question",
            "latency_ms": latency_ms, "cost_usd": resp.cost_usd,
        }

    _, gold_rows = executor.run(project.id, case.gold_sql)
    gold = _denote(gold_rows)
    matched_sql = None
    for card in ok_cards:
        if _denote(card.rows) == gold:
            matched_sql = card.sql
            break

    intent_ok = case.expect_intent is None or any(
        c.type == case.expect_intent for c in resp.cards
    )
    return {
        "matched": matched_sql is not None,
        "valid": valid and not resp.degraded,
        "intent_ok": intent_ok,
        "sql": matched_sql or (resp.cards[0].sql if resp.cards else None),
        "error": None if matched_sql else "no card matched the gold result set",
        "latency_ms": latency_ms,
        "cost_usd": resp.cost_usd,
    }
