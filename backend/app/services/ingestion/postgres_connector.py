"""Read-only Postgres connector for client databases.

Read-only is enforced defensively even if the supplied role has write access:
every connection sets `default_transaction_read_only=on` and a `statement_timeout`.
Only introspection/SELECT SQL is ever issued. The connection string itself is
Fernet-encrypted at rest by the caller and never logged.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.errors import AppError


class PgConnectionError(AppError):
    code = "connection_error"


def read_only_options(statement_timeout_ms: int) -> str:
    """libpq `options` string: force read-only txns + a hard statement timeout."""
    return (
        f"-c default_transaction_read_only=on "
        f"-c statement_timeout={int(statement_timeout_ms)} "
        f"-c idle_in_transaction_session_timeout={int(statement_timeout_ms)}"
    )


# Introspection stays out of pg internal schemas and only reads catalogs.
_TABLES_SQL = """
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name
"""

_COLUMNS_SQL = """
SELECT table_schema, table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position
"""


@dataclass
class PgColumn:
    name: str
    dtype: str
    nullable: bool


@dataclass
class PgTable:
    schema: str
    name: str
    columns: list[PgColumn]

    @property
    def qualified(self) -> str:
        return f"{self.schema}.{self.name}"


class PostgresConnector:
    def __init__(self, dsn: str, statement_timeout_ms: int | None = None) -> None:
        self._dsn = dsn
        self._timeout = statement_timeout_ms or get_settings().sql_statement_timeout_ms

    def _connect(self):
        import psycopg  # imported lazily so the module loads without a live driver need

        return psycopg.connect(
            self._dsn,
            options=read_only_options(self._timeout),
            autocommit=True,
        )

    def test_connection(self) -> bool:
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone()[0] == 1
        except Exception as exc:  # noqa: BLE001 - surface a clean error, hide internals
            raise PgConnectionError("Could not connect to the Postgres database") from exc

    def introspect(self) -> list[PgTable]:
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(_TABLES_SQL)
                tables: dict[tuple[str, str], list[PgColumn]] = {
                    (s, t): [] for s, t in cur.fetchall()
                }
                cur.execute(_COLUMNS_SQL)
                for schema, table, col, dtype, nullable in cur.fetchall():
                    key = (schema, table)
                    if key in tables:
                        tables[key].append(
                            PgColumn(name=col, dtype=dtype, nullable=(nullable == "YES"))
                        )
        except PgConnectionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PgConnectionError("Schema introspection failed") from exc
        return [PgTable(schema=s, name=t, columns=cols) for (s, t), cols in tables.items()]
