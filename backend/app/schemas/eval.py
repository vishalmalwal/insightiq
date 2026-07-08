"""Eval API schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvalCaseResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    passed: bool
    generated_sql: str | None
    error: str | None
    latency_ms: float | None
    cost_usd: float | None


class EvalRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    suite_version: str
    provider: str
    git_sha: str | None
    exec_accuracy: float | None
    valid_sql_rate: float | None
    intent_accuracy: float | None
    avg_latency_ms: float | None
    total_cost_usd: float | None
    started_at: datetime | None
    finished_at: datetime | None


class EvalRunDetail(EvalRunOut):
    cases: list[EvalCaseResultOut] = []
