"""Ask-pipeline schemas: the structured plan the planner emits, and the per-intent
result cards the executor produces. The plan is the LLM's structured-output target
(no free-text parsing). Charts/insight captions are added in Phase 4.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.semantic_layer import Grain

IntentType = Literal["trend", "breakdown", "comparison", "kpi", "distribution"]
FilterOp = Literal["=", "!=", ">", "<", ">=", "<=", "in", "between"]


class IntentFilter(BaseModel):
    dimension: str                       # semantic dimension name
    op: FilterOp
    value: Any                           # scalar, or list for in/between


class AnalysisIntent(BaseModel):
    id: str
    type: IntentType
    title: str
    entity: str                          # base entity (semantic-layer name)
    measures: list[str] = Field(default_factory=list)      # measure names
    breakdown: str | None = None         # categorical dimension to group by
    time_dimension: str | None = None    # explicit; else builder picks the primary
    time_grain: Grain | None = None
    filters: list[IntentFilter] = Field(default_factory=list)
    limit: int | None = None


class AnalysisPlan(BaseModel):
    question: str
    intents: list[AnalysisIntent] = Field(default_factory=list)  # 1..6


class IntentCard(BaseModel):
    intent_id: str
    type: IntentType
    title: str
    ok: bool
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    caption: str | None = None
    error: str | None = None


class AskResponse(BaseModel):
    ask_request_id: str | None = None
    dashboard_id: str | None = None
    question: str
    degraded: bool = False
    message: str | None = None
    cache_hit: bool = False
    cost_usd: float = 0.0
    plan: AnalysisPlan
    cards: list[IntentCard] = Field(default_factory=list)


class AskRequestBody(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    date_from: str | None = None  # ISO date; applies a global time filter
    date_to: str | None = None


class DashboardOut(BaseModel):
    id: str
    project_id: str | None = None
    created_at: str
    layout: list[dict[str, Any]] = Field(default_factory=list)
    response: AskResponse


class DashboardLayoutUpdate(BaseModel):
    layout: list[dict[str, Any]]


class DashboardListItem(BaseModel):
    id: str
    question: str
    created_at: str
