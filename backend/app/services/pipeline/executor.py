"""Sandboxed query executor (DuckDB path).

Runs guarded, SELECT-only SQL read-only with a wall-clock timeout (interrupts the
connection on overrun), a row cap (enforced by the guard's LIMIT), and a byte cap
on the materialised result. Postgres client sources run through the read-only
connector (dedicated txn + statement_timeout); the guard is shared.
"""
from __future__ import annotations

import datetime as _dt
import decimal as _dec
import threading
import uuid
from typing import Any

from app.core.config import get_settings
from app.db.duckdb_manager import DuckDBManager
from app.services.pipeline.errors import ExecError


def _coerce(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (_dt.date, _dt.datetime, _dt.time)):
        return value.isoformat()
    if isinstance(value, _dec.Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


class DuckDBExecutor:
    def __init__(self, duckdb: DuckDBManager | None = None) -> None:
        self._duck = duckdb or DuckDBManager()
        s = get_settings()
        self._timeout_s = s.sql_statement_timeout_ms / 1000.0
        self._max_bytes = s.sql_max_result_bytes

    def run(self, project_id: uuid.UUID, sql: str) -> tuple[list[str], list[list[Any]]]:
        con = self._duck.connect(str(project_id), read_only=True)
        box: dict[str, Any] = {}

        def work() -> None:
            try:
                rel = con.execute(sql)
                box["cols"] = [d[0] for d in rel.description]
                box["rows"] = rel.fetchall()
            except Exception as exc:  # noqa: BLE001 - surfaced below as ExecError
                box["err"] = exc

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        thread.join(timeout=self._timeout_s)
        if thread.is_alive():
            try:
                con.interrupt()
            finally:
                thread.join(1.0)
                con.close()
            raise ExecError(f"Query exceeded the {self._timeout_s:.0f}s time limit")

        try:
            if "err" in box:
                raise ExecError(str(box["err"]))
            columns: list[str] = box["cols"]
            rows = [[_coerce(v) for v in row] for row in box["rows"]]
            rows = self._apply_byte_cap(rows)
            return columns, rows
        finally:
            con.close()

    def _apply_byte_cap(self, rows: list[list[Any]]) -> list[list[Any]]:
        total = 0
        capped: list[list[Any]] = []
        for row in rows:
            total += sum(len(str(v)) for v in row)
            if total > self._max_bytes:
                break
            capped.append(row)
        return capped
