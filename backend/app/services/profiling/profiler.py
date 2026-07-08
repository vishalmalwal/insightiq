"""Profile a DuckDB table: types, null %, distinct, min/max, sample values.

Profiles feed the Phase 2 semantic-layer generator, so the inferred
`semantic_type` (numeric/time/categorical/boolean/text) matters here.
"""
from __future__ import annotations

import uuid

from app.core.errors import NotFoundError
from app.db.duckdb_manager import DuckDBManager
from app.schemas.data_sources import ColumnProfile, TableProfile

_TIME_HINTS = ("DATE", "TIMESTAMP", "TIME")
_FLOAT_HINTS = ("DECIMAL", "DOUBLE", "FLOAT", "REAL", "NUMERIC")

# A low-cardinality text/integer column reads as a dimension, not a measure/free text.
_CATEGORICAL_MAX_DISTINCT = 50


def _one(cursor) -> tuple:
    row = cursor.fetchone()
    assert row is not None  # aggregate/count queries always return a row
    return row


def _semantic_type(dtype: str, distinct: int, row_count: int) -> str:
    d = dtype.upper()
    if d.startswith("BOOL"):
        return "boolean"
    if any(h in d for h in _TIME_HINTS):
        return "time"
    if any(h in d for h in _FLOAT_HINTS):
        return "numeric"  # measures are floats/decimals — always numeric
    if "INT" in d:
        # integer ids/codes with few distinct values behave like categories
        if distinct <= _CATEGORICAL_MAX_DISTINCT and distinct < max(row_count, 1):
            return "categorical"
        return "numeric"
    # strings
    if distinct <= _CATEGORICAL_MAX_DISTINCT:
        return "categorical"
    return "text"


class ProfilingService:
    def __init__(self, duckdb: DuckDBManager | None = None) -> None:
        self._duck = duckdb or DuckDBManager()

    def profile_table(self, project_id: uuid.UUID, table: str) -> TableProfile:
        pid = str(project_id)
        if not self._duck.exists(pid):
            raise NotFoundError(f"No data store for project {project_id}")
        con = self._duck.connect(pid, read_only=True)
        try:
            existing = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if table not in existing:
                raise NotFoundError(f"Table '{table}' not found")

            row_count = int(_one(con.execute(f'SELECT COUNT(*) FROM "{table}"'))[0])
            described = con.execute(f'DESCRIBE "{table}"').fetchall()  # (name, type, ...)

            columns: list[ColumnProfile] = []
            for col_name, col_type, *_ in described:
                non_null, distinct = _one(
                    con.execute(
                        f'SELECT COUNT("{col_name}"), COUNT(DISTINCT "{col_name}") FROM "{table}"'
                    )
                )
                non_null = int(non_null)
                distinct = int(distinct)
                null_count = row_count - non_null
                null_pct = round((null_count / row_count) * 100, 2) if row_count else 0.0

                sem = _semantic_type(str(col_type), distinct, row_count)

                col_min = col_max = None
                if sem in ("numeric", "time") and non_null:
                    col_min, col_max = _one(
                        con.execute(f'SELECT MIN("{col_name}"), MAX("{col_name}") FROM "{table}"')
                    )

                samples = [
                    r[0]
                    for r in con.execute(
                        f'SELECT DISTINCT "{col_name}" FROM "{table}" '
                        f'WHERE "{col_name}" IS NOT NULL LIMIT 5'
                    ).fetchall()
                ]

                columns.append(
                    ColumnProfile(
                        name=str(col_name),
                        dtype=str(col_type),
                        semantic_type=sem,
                        null_count=null_count,
                        null_pct=null_pct,
                        distinct_count=distinct,
                        min=_coerce(col_min),
                        max=_coerce(col_max),
                        sample_values=[_coerce(s) for s in samples],
                    )
                )
            return TableProfile(table=table, row_count=row_count, columns=columns)
        finally:
            con.close()


def _coerce(value: object) -> object | None:
    """Make DuckDB values JSON-serialisable (dates/decimals → str/float)."""
    if value is None:
        return None
    import datetime as _dt
    import decimal as _dec

    if isinstance(value, (_dt.date, _dt.datetime, _dt.time)):
        return value.isoformat()
    if isinstance(value, _dec.Decimal):
        return float(value)
    return value
