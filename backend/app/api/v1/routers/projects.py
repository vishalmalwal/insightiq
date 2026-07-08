"""Projects CRUD. Mutating routes are gated by the shared-secret access boundary."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, IngestionDep, ProjectDep
from app.core.security import verify_app_access
from app.repositories.projects import ProjectRepository
from app.schemas.projects import Project, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_app_access)],
    summary="Create a project",
)
async def create_project(body: ProjectCreate, session: DbSession) -> Project:
    project = ProjectRepository(session).create(name=body.name, data_source=body.source)
    return Project.model_validate(project)


@router.get("", response_model=list[Project], summary="List projects")
async def list_projects(session: DbSession) -> list[Project]:
    return [Project.model_validate(p) for p in ProjectRepository(session).list()]


@router.get("/{project_id}", response_model=Project, summary="Get a project")
async def get_project_route(project: ProjectDep) -> Project:
    return Project.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_app_access)],
    summary="Delete a project (and its data store)",
)
async def delete_project(
    project: ProjectDep, session: DbSession, ingestion: IngestionDep
) -> None:
    ingestion._duck.delete(str(project.id))  # drop the DuckDB store too
    ProjectRepository(session).delete(project)
