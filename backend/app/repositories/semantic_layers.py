"""Versioned storage for semantic layers. Versions are immutable; newest is active."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SemanticLayer
from app.schemas.semantic_layer import SemanticLayerSpec


class SemanticLayerRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def get_active(self, project_id: uuid.UUID) -> SemanticLayer | None:
        return self._s.scalar(
            select(SemanticLayer)
            .where(SemanticLayer.project_id == project_id, SemanticLayer.is_active.is_(True))
            .order_by(SemanticLayer.version.desc())
        )

    def get_version(self, project_id: uuid.UUID, version: int) -> SemanticLayer | None:
        return self._s.scalar(
            select(SemanticLayer).where(
                SemanticLayer.project_id == project_id, SemanticLayer.version == version
            )
        )

    def list_versions(self, project_id: uuid.UUID) -> list[SemanticLayer]:
        return list(
            self._s.scalars(
                select(SemanticLayer)
                .where(SemanticLayer.project_id == project_id)
                .order_by(SemanticLayer.version.desc())
            )
        )

    def _max_version(self, project_id: uuid.UUID) -> int:
        rows = self._s.scalars(
            select(SemanticLayer.version).where(SemanticLayer.project_id == project_id)
        )
        return max(list(rows), default=0)

    def save_new_version(
        self, project_id: uuid.UUID, spec: SemanticLayerSpec, created_by: str
    ) -> SemanticLayer:
        # Deactivate whatever is currently active.
        for row in self._s.scalars(
            select(SemanticLayer).where(
                SemanticLayer.project_id == project_id, SemanticLayer.is_active.is_(True)
            )
        ):
            row.is_active = False

        version = self._max_version(project_id) + 1
        spec.version = version
        spec.project_id = str(project_id)
        record = SemanticLayer(
            project_id=project_id,
            version=version,
            spec=spec.model_dump(exclude_none=True),
            is_active=True,
            created_by=created_by,
        )
        self._s.add(record)
        self._s.flush()
        return record
