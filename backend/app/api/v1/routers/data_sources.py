"""Ingestion + profiling routes, scoped to a project."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import DbSession, IngestionDep, ProfilingDep, ProjectDep
from app.core.crypto import encrypt
from app.core.security import verify_app_access
from app.repositories.data_sources import DataSourceRepository
from app.schemas.data_sources import (
    ConnectionCreate,
    TableMeta,
    TableProfile,
    UploadResult,
)
from app.services.ingestion.postgres_connector import PostgresConnector

router = APIRouter(prefix="/projects/{project_id}", tags=["data"])


@router.post(
    "/uploads",
    response_model=UploadResult,
    dependencies=[Depends(verify_app_access)],
    summary="Upload a CSV/XLSX into the project's DuckDB store",
)
async def upload_file(
    project: ProjectDep, file: UploadFile, ingestion: IngestionDep
) -> UploadResult:
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        tables = ingestion.ingest_file(project.id, tmp_path, file.filename or "upload")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return UploadResult(tables=tables)


@router.post(
    "/connections",
    response_model=UploadResult,
    dependencies=[Depends(verify_app_access)],
    summary="Connect a read-only Postgres database (introspect its schema)",
)
async def create_connection(
    project: ProjectDep, body: ConnectionCreate, session: DbSession
) -> UploadResult:
    connector = PostgresConnector(body.connection_string)
    tables = connector.introspect()  # read-only; enforces timeout + RO txn
    # Persist the encrypted DSN only after a successful introspection.
    DataSourceRepository(session).create(
        project_id=project.id,
        kind="postgres",
        config_encrypted=encrypt(body.connection_string),
    )
    return UploadResult(
        tables=[
            TableMeta(name=t.qualified, row_count=-1, column_count=len(t.columns))
            for t in tables
        ]
    )


@router.get("/tables", response_model=list[TableMeta], summary="List project tables")
async def list_tables(project: ProjectDep, ingestion: IngestionDep) -> list[TableMeta]:
    return ingestion.list_tables(project.id)


@router.get(
    "/tables/{table}/profile",
    response_model=TableProfile,
    summary="Profile a table",
)
async def profile_table(
    project: ProjectDep, table: str, profiling: ProfilingDep
) -> TableProfile:
    return profiling.profile_table(project.id, table)
