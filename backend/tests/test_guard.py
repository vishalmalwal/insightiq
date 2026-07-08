"""Adversarial tests for the SQL safety stack (DESIGN §7)."""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.errors import UnsafeSQLError
from app.schemas.semantic_layer import DataSourceSpec, Entity, SemanticLayerSpec
from app.services.pipeline.guard import SqlGuard

SEM = SemanticLayerSpec(
    data_source=DataSourceSpec(type="duckdb", dialect="duckdb"),
    entities=[Entity(name="orders", table="orders"), Entity(name="customers", table="customers")],
)


def guard() -> SqlGuard:
    return SqlGuard(get_settings().sql_row_limit)


def test_allows_plain_select_and_injects_limit() -> None:
    out = guard().validate("SELECT region FROM customers", SEM, "duckdb")
    assert "LIMIT" in out.upper()


def test_allows_declared_join() -> None:
    sql = "SELECT c.region FROM orders AS o JOIN customers AS c ON o.customer_id=c.customer_id"
    assert guard().validate(sql, SEM, "duckdb")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE customers",
        "UPDATE orders SET amount = 0",
        "DELETE FROM orders",
        "SELECT 1 FROM orders; DROP TABLE customers",          # multi-statement
        "PRAGMA database_list",                                 # pragma
        "ATTACH 'evil.db' AS evil",                             # attach
        "COPY orders TO 'out.csv'",                             # copy
        "SELECT 1 FROM orders WHERE 1=1; INSTALL httpfs",       # install
        "SELECT * INTO evil FROM orders",                       # select into
        "SELECT amount FROM orders UNION SELECT pw FROM secret_users",  # outside allowlist
    ],
)
def test_blocks_dangerous_sql(sql: str) -> None:
    with pytest.raises(UnsafeSQLError):
        guard().validate(sql, SEM, "duckdb")


def test_comment_injection_is_neutralised_not_executed() -> None:
    # The trailing "-- ; DROP" survives only as an inert comment; assert that the
    # guarded statement is still a single SELECT with no live DROP in the tree.
    import sqlglot
    from sqlglot import exp

    out = guard().validate("SELECT region FROM customers -- ; DROP TABLE orders", SEM, "duckdb")
    parsed = sqlglot.parse_one(out, read="duckdb")
    assert isinstance(parsed, exp.Select)
    assert parsed.find(exp.Drop) is None


def test_union_within_allowlist_is_allowed() -> None:
    sql = "SELECT region FROM customers UNION SELECT status FROM orders"
    assert guard().validate(sql, SEM, "duckdb")
