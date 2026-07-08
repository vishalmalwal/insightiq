"""SQL builder: semantic-only construction, join resolution, time defaulting."""
from __future__ import annotations

import pytest

from app.db.duckdb_manager import DuckDBManager
from app.repositories.projects import ProjectRepository
from app.schemas.pipeline import AnalysisIntent, IntentFilter
from app.services.pipeline.errors import BuildError
from app.services.pipeline.sql_builder import SqlBuilder
from app.services.sample_data.seed import seed_sample_data
from app.services.semantic_layer.generator import SemanticLayerGenerator


def _ecom_sem(db_session):
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    return SemanticLayerGenerator(DuckDBManager()).build(ecom.id, dialect="duckdb")


def test_trend_defaults_to_event_date_not_signup(db_session) -> None:
    sem = _ecom_sem(db_session)
    intent = AnalysisIntent(
        id="i1", type="trend", title="revenue by month", entity="order_items",
        measures=["amount"], time_grain="month",
    )
    sql = SqlBuilder().build(intent, sem).lower()
    assert "order_date" in sql          # primary event date
    assert "signup_date" not in sql     # never the signup date
    assert "date_trunc('month'" in sql


def test_comparison_resolves_join_to_region(db_session) -> None:
    sem = _ecom_sem(db_session)
    intent = AnalysisIntent(
        id="i1", type="comparison", title="rev by region", entity="order_items",
        measures=["amount"], breakdown="region", time_grain="year",
    )
    sql = SqlBuilder().build(intent, sem).lower()
    assert "join orders" in sql and "join customers" in sql
    assert "customers.region" in sql
    assert "sum(order_items.amount)" in sql


def test_unknown_measure_raises_build_error(db_session) -> None:
    sem = _ecom_sem(db_session)
    intent = AnalysisIntent(
        id="i1", type="kpi", title="x", entity="orders", measures=["does_not_exist"]
    )
    with pytest.raises(BuildError):
        SqlBuilder().build(intent, sem)


def test_filter_values_are_escaped(db_session) -> None:
    sem = _ecom_sem(db_session)
    intent = AnalysisIntent(
        id="i1", type="breakdown", title="x", entity="orders", measures=["orders_count"],
        breakdown="status",
        filters=[IntentFilter(dimension="status", op="=", value="o'brien'; DROP")],
    )
    sql = SqlBuilder().build(intent, sem)
    # The single quote is doubled → a safe string literal, no statement break.
    assert "o''brien'"  # doubled quote present
    assert "'; DROP" not in sql.replace("''", "")  # no live break-out
