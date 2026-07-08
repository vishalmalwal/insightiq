"""App-metadata ORM models (Postgres in prod, SQLite in tests).

Full schema is defined now so we migrate once; Phase 1 actively uses `project`
and `data_source`, later phases fill in the rest.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Project(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(120), unique=True, nullable=False)
    # 'sample' | 'duckdb' | 'postgres'
    data_source: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    sources: Mapped[list[DataSource]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(sa.String(20), nullable=False)  # 'duckdb' | 'postgres'
    # Fernet-encrypted client PG connection string; NULL for duckdb/sample.
    config_encrypted: Mapped[bytes | None] = mapped_column(sa.LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="sources")


class SemanticLayer(Base):
    __tablename__ = "semantic_layer"
    __table_args__ = (sa.UniqueConstraint("project_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    spec: Mapped[dict] = mapped_column(JSONType, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


class AskRequest(Base):
    __tablename__ = "ask_request"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(sa.Text, nullable=False)
    sem_version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    plan: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(sa.Numeric(10, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


class Dashboard(Base):
    __tablename__ = "dashboard"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    ask_request_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("ask_request.id", ondelete="CASCADE"), nullable=False, index=True
    )
    layout: Mapped[Any] = mapped_column(JSONType, nullable=False)
    charts: Mapped[dict] = mapped_column(JSONType, nullable=False)


class EvalRun(Base):
    __tablename__ = "eval_run"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    suite_version: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(20), nullable=False, server_default="mock")
    git_sha: Mapped[str | None] = mapped_column(sa.String(40), nullable=True)
    exec_accuracy: Mapped[float | None] = mapped_column(sa.Numeric(5, 4), nullable=True)
    valid_sql_rate: Mapped[float | None] = mapped_column(sa.Numeric(5, 4), nullable=True)
    intent_accuracy: Mapped[float | None] = mapped_column(sa.Numeric(5, 4), nullable=True)
    avg_latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(sa.Numeric(10, 6), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)


class EvalCaseResult(Base):
    __tablename__ = "eval_case_result"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("eval_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    passed: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(sa.Numeric(10, 6), nullable=True)


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(sa.String(40), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    model: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    input_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(sa.Numeric(10, 6), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


class QueryCache(Base):
    __tablename__ = "query_cache"

    key_hash: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
