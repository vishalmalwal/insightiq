"""Persistence for eval runs + per-case results."""
from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EvalCaseResult, EvalRun


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.UTC)


class EvalRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create_run(self, suite_version: str, provider: str, git_sha: str | None) -> EvalRun:
        run = EvalRun(
            suite_version=suite_version, provider=provider, git_sha=git_sha, started_at=_now()
        )
        self._s.add(run)
        self._s.flush()
        return run

    def add_case_result(
        self,
        run_id: uuid.UUID,
        case_id: str,
        *,
        passed: bool,
        generated_sql: str | None,
        error: str | None,
        latency_ms: float,
        cost_usd: float,
    ) -> None:
        self._s.add(
            EvalCaseResult(
                run_id=run_id,
                case_id=case_id,
                passed=passed,
                generated_sql=generated_sql,
                error=error,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
        )

    def finalize_run(
        self,
        run: EvalRun,
        *,
        exec_accuracy: float,
        valid_sql_rate: float,
        intent_accuracy: float,
        avg_latency_ms: float,
        total_cost_usd: float,
    ) -> None:
        run.exec_accuracy = exec_accuracy
        run.valid_sql_rate = valid_sql_rate
        run.intent_accuracy = intent_accuracy
        run.avg_latency_ms = int(avg_latency_ms)
        run.total_cost_usd = total_cost_usd
        run.finished_at = _now()
        self._s.flush()

    def list_runs(self, limit: int = 20) -> list[EvalRun]:
        return list(
            self._s.scalars(select(EvalRun).order_by(EvalRun.started_at.desc()).limit(limit))
        )

    def get_run(self, run_id: uuid.UUID) -> EvalRun | None:
        return self._s.get(EvalRun, run_id)

    def case_results(self, run_id: uuid.UUID) -> list[EvalCaseResult]:
        return list(
            self._s.scalars(
                select(EvalCaseResult)
                .where(EvalCaseResult.run_id == run_id)
                .order_by(EvalCaseResult.case_id)
            )
        )
