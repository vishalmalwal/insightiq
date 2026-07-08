"""Read-only enforcement + schema introspection (no live DB needed)."""
from __future__ import annotations

from app.services.ingestion.postgres_connector import PostgresConnector, read_only_options


def test_read_only_options_enforce_ro_and_timeout() -> None:
    opts = read_only_options(15000)
    assert "default_transaction_read_only=on" in opts
    assert "statement_timeout=15000" in opts
    assert "idle_in_transaction_session_timeout=15000" in opts


class _FakeCursor:
    def __init__(self) -> None:
        self._q = ""

    def execute(self, sql: str) -> None:
        self._q = sql

    def fetchone(self):
        return (1,)

    def fetchall(self):
        if "information_schema.tables" in self._q:
            return [("public", "orders"), ("public", "customers")]
        if "information_schema.columns" in self._q:
            return [
                ("public", "orders", "id", "integer", "NO"),
                ("public", "orders", "amount", "numeric", "YES"),
                ("public", "customers", "id", "integer", "NO"),
            ]
        return []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeConn:
    def cursor(self):
        return _FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_introspect_assembles_tables(monkeypatch) -> None:
    monkeypatch.setattr(PostgresConnector, "_connect", lambda self: _FakeConn())
    conn = PostgresConnector("postgresql://x/y")
    assert conn.test_connection() is True

    tables = {t.qualified: t for t in conn.introspect()}
    assert set(tables) == {"public.orders", "public.customers"}
    assert [c.name for c in tables["public.orders"].columns] == ["id", "amount"]
    assert tables["public.orders"].columns[1].nullable is True
