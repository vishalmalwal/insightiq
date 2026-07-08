"""Load uploaded CSV/XLSX files into a project's DuckDB store.

CSV/TSV go through DuckDB's native `read_csv_auto` so column *types* (dates,
ints, floats, booleans) are inferred correctly. XLSX is read via pandas (DuckDB
has no native reader) and registered.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import duckdb
import pandas as pd

from app.core.errors import ValidationError
from app.db.duckdb_manager import DuckDBManager
from app.schemas.data_sources import TableMeta
from app.services.ingestion.naming import safe_identifier

_MAX_BYTES = 100 * 1024 * 1024  # 100 MB upload cap
_CSV_SUFFIXES = (".csv", ".tsv", ".txt")
_XLSX_SUFFIXES = (".xlsx", ".xls")


def _table_meta(con: duckdb.DuckDBPyConnection, name: str) -> TableMeta:
    row = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()
    rows = int(row[0]) if row else 0
    cols = len(con.execute(f'DESCRIBE "{name}"').fetchall())
    return TableMeta(name=name, row_count=rows, column_count=cols)


class IngestionService:
    def __init__(self, duckdb_manager: DuckDBManager | None = None) -> None:
        self._duck = duckdb_manager or DuckDBManager()

    def ingest_file(
        self, project_id: uuid.UUID, file_path: str | Path, filename: str
    ) -> list[TableMeta]:
        path = Path(file_path)
        if not path.exists():
            raise ValidationError("Uploaded file not found on disk")
        if path.stat().st_size > _MAX_BYTES:
            raise ValidationError("File exceeds the 100 MB upload limit")

        suffix = Path(filename).suffix.lower()
        stem = safe_identifier(Path(filename).stem)
        pid = str(project_id)

        con = self._duck.connect(pid, read_only=False)
        results: list[TableMeta] = []
        try:
            if suffix in _CSV_SUFFIXES:
                con.execute(
                    f'CREATE OR REPLACE TABLE "{stem}" AS '
                    "SELECT * FROM read_csv_auto(?, header=true, sample_size=-1)",
                    [str(path)],
                )
                meta = _table_meta(con, stem)
                if meta.row_count:
                    results.append(meta)
                else:
                    con.execute(f'DROP TABLE "{stem}"')
            elif suffix in _XLSX_SUFFIXES:
                sheets = pd.read_excel(path, sheet_name=None)
                multi = len(sheets) > 1
                for sheet_name, frame in sheets.items():
                    if frame.empty:
                        continue
                    name = f"{stem}_{safe_identifier(sheet_name)}" if multi else stem
                    con.register("_ingest_df", frame)
                    con.execute(
                        f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _ingest_df'
                    )
                    con.unregister("_ingest_df")
                    results.append(_table_meta(con, name))
            else:
                raise ValidationError(f"Unsupported file type: {suffix or '(none)'}")
        finally:
            con.close()

        self._duck.persist(pid)  # no-op for local; uploads to R2 in deploy
        if not results:
            raise ValidationError("No non-empty tables found in the uploaded file")
        return results

    def ingest_frames(
        self, project_id: uuid.UUID, frames: dict[str, pd.DataFrame]
    ) -> list[TableMeta]:
        """Load in-memory DataFrames into the project's DuckDB store (used by the seeder)."""
        pid = str(project_id)
        results: list[TableMeta] = []
        con = self._duck.connect(pid, read_only=False)
        try:
            for table, frame in frames.items():
                con.register("_ingest_df", frame)
                con.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM _ingest_df')
                con.unregister("_ingest_df")
                results.append(_table_meta(con, table))
        finally:
            con.close()
        self._duck.persist(pid)
        return results

    def list_tables(self, project_id: uuid.UUID) -> list[TableMeta]:
        pid = str(project_id)
        if not self._duck.exists(pid):
            return []
        con = self._duck.connect(pid, read_only=True)
        try:
            names = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
            return [_table_meta(con, n) for n in names]
        finally:
            con.close()
