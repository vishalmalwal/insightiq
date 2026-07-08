"""Semantic-layer spec models (DESIGN §5) + API request/response schemas.

These are the single in-code representation used for validation, JSON storage
(`semantic_layer.spec`), YAML (de)serialisation for the editor, and as the
structured-output schema handed to the LLM.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AggType = Literal["sum", "avg", "count", "count_distinct", "min", "max"]
DimType = Literal["time", "categorical", "boolean", "numeric"]
Grain = Literal["day", "week", "month", "quarter", "year"]
FormatType = Literal["currency", "number", "percent"]
JoinType = Literal["many_to_one", "one_to_many", "one_to_one"]
Dialect = Literal["duckdb", "postgres"]


class Dimension(BaseModel):
    name: str
    type: DimType
    sql: str
    grain: Grain | None = None
    description: str = ""
    synonyms: list[str] = Field(default_factory=list)


class Measure(BaseModel):
    name: str
    agg: AggType
    sql: str
    format: FormatType | None = None
    description: str = ""
    synonyms: list[str] = Field(default_factory=list)


class Join(BaseModel):
    to: str
    type: JoinType
    on: str


class Entity(BaseModel):
    name: str
    table: str
    description: str = ""
    primary_key: list[str] = Field(default_factory=list)
    # The entity's main event date (e.g. order_date) — the default for time-based
    # questions that don't name a date. Set by the generator; editable.
    primary_time_dimension: str | None = None
    dimensions: list[Dimension] = Field(default_factory=list)
    measures: list[Measure] = Field(default_factory=list)
    joins: list[Join] = Field(default_factory=list)


class Metric(BaseModel):
    name: str
    expr: str
    description: str = ""
    format: FormatType | None = None


class DataSourceSpec(BaseModel):
    type: Dialect
    dialect: Dialect


class SemanticLayerSpec(BaseModel):
    """The full, versioned semantic layer for a project."""

    version: int = 1
    project_id: str | None = None
    data_source: DataSourceSpec
    entities: list[Entity] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)


# ---- API response / request ----


class VersionMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    is_active: bool
    created_by: str | None
    created_at: datetime


class SemanticLayerOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    version: int
    is_active: bool
    created_by: str | None
    created_at: datetime
    spec: SemanticLayerSpec
    yaml: str


class SemanticLayerUpdate(BaseModel):
    """Edit payload from the UI — the raw YAML from the editor textarea."""

    yaml: str
