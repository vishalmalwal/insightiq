"""Data-source / ingestion / profiling API schemas."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SemanticType = Literal["numeric", "time", "categorical", "boolean", "text"]


class TableMeta(BaseModel):
    name: str
    row_count: int
    column_count: int


class UploadResult(BaseModel):
    tables: list[TableMeta]


class ConnectionCreate(BaseModel):
    # Read-only client Postgres. Value is encrypted at rest, never logged.
    connection_string: str = Field(min_length=1)


class ColumnProfile(BaseModel):
    name: str
    dtype: str                       # physical type as reported by the engine
    semantic_type: SemanticType      # inferred role
    null_count: int
    null_pct: float
    distinct_count: int
    min: Any | None = None
    max: Any | None = None
    sample_values: list[Any] = Field(default_factory=list)


class TableProfile(BaseModel):
    table: str
    row_count: int
    columns: list[ColumnProfile]
