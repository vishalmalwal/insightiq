"""Persisted dashboards — a saved question result, shareable/reloadable by id."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AskRequest, Dashboard


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self, ask_request_id: uuid.UUID, layout: list | dict, charts: dict
    ) -> Dashboard:
        row = Dashboard(ask_request_id=ask_request_id, layout=layout, charts=charts)
        self._s.add(row)
        self._s.flush()
        return row

    def get(self, dashboard_id: uuid.UUID) -> Dashboard | None:
        return self._s.get(Dashboard, dashboard_id)

    def update_layout(
        self, dashboard_id: uuid.UUID, layout: list[dict[str, object]]
    ) -> Dashboard | None:
        row = self._s.get(Dashboard, dashboard_id)
        if row is None:
            return None
        row.layout = layout
        self._s.flush()
        return row

    def ask_request_of(self, dashboard: Dashboard) -> AskRequest | None:
        return self._s.get(AskRequest, dashboard.ask_request_id)

    def project_id_of(self, dashboard: Dashboard) -> uuid.UUID | None:
        ar = self.ask_request_of(dashboard)
        return ar.project_id if ar else None

    def list_by_project(self, project_id: uuid.UUID, limit: int = 20) -> list[Dashboard]:
        return list(
            self._s.scalars(
                select(Dashboard)
                .join(AskRequest, Dashboard.ask_request_id == AskRequest.id)
                .where(AskRequest.project_id == project_id)
                .order_by(AskRequest.created_at.desc())
                .limit(limit)
            )
        )
