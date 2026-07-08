"""Data access for data sources (upload/connection records)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DataSource


class DataSourceRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self, *, project_id: uuid.UUID, kind: str, config_encrypted: bytes | None = None
    ) -> DataSource:
        ds = DataSource(project_id=project_id, kind=kind, config_encrypted=config_encrypted)
        self._s.add(ds)
        self._s.flush()
        return ds

    def list_for_project(self, project_id: uuid.UUID) -> list[DataSource]:
        return list(
            self._s.scalars(select(DataSource).where(DataSource.project_id == project_id))
        )
