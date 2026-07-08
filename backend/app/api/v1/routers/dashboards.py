"""Persisted dashboards — shareable/reloadable question results."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, ProjectDep
from app.core.errors import NotFoundError
from app.core.security import verify_app_access
from app.repositories.dashboards import DashboardRepository
from app.schemas.pipeline import (
    AskResponse,
    DashboardLayoutUpdate,
    DashboardListItem,
    DashboardOut,
)

router = APIRouter(tags=["dashboards"])


@router.get("/dashboards/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(dashboard_id: uuid.UUID, session: DbSession) -> DashboardOut:
    repo = DashboardRepository(session)
    dash = repo.get(dashboard_id)
    if dash is None:
        raise NotFoundError(f"Dashboard {dashboard_id} not found")
    ar = repo.ask_request_of(dash)
    return DashboardOut(
        id=str(dash.id),
        project_id=str(ar.project_id) if ar else None,
        created_at=ar.created_at.isoformat() if ar else "",
        layout=list(dash.layout or []),
        response=AskResponse.model_validate(dash.charts),
    )


@router.patch(
    "/dashboards/{dashboard_id}",
    response_model=DashboardOut,
    dependencies=[Depends(verify_app_access)],
    summary="Persist a user-adjusted grid layout",
)
async def update_dashboard_layout(
    dashboard_id: uuid.UUID, body: DashboardLayoutUpdate, session: DbSession
) -> DashboardOut:
    repo = DashboardRepository(session)
    dash = repo.update_layout(dashboard_id, body.layout)
    if dash is None:
        raise NotFoundError(f"Dashboard {dashboard_id} not found")
    ar = repo.ask_request_of(dash)
    return DashboardOut(
        id=str(dash.id),
        project_id=str(ar.project_id) if ar else None,
        created_at=ar.created_at.isoformat() if ar else "",
        layout=list(dash.layout or []),
        response=AskResponse.model_validate(dash.charts),
    )


@router.get("/projects/{project_id}/dashboards", response_model=list[DashboardListItem])
async def list_dashboards(project: ProjectDep, session: DbSession) -> list[DashboardListItem]:
    repo = DashboardRepository(session)
    out: list[DashboardListItem] = []
    for d in repo.list_by_project(project.id):
        ar = repo.ask_request_of(d)
        out.append(
            DashboardListItem(
                id=str(d.id),
                question=str(d.charts.get("question", "")),
                created_at=ar.created_at.isoformat() if ar else "",
            )
        )
    return out
