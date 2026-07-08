"""Semantic-layer generation, versioned storage, and editing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, ProjectDep, SemanticGenDep, project_dialect
from app.core.errors import NotFoundError
from app.core.security import verify_app_access
from app.db.models import SemanticLayer
from app.repositories.semantic_layers import SemanticLayerRepository
from app.schemas.semantic_layer import (
    SemanticLayerOut,
    SemanticLayerSpec,
    SemanticLayerUpdate,
    VersionMeta,
)
from app.services.semantic_layer.yaml_io import spec_to_yaml, yaml_to_spec

router = APIRouter(prefix="/projects/{project_id}/semantic-layer", tags=["semantic-layer"])


def _to_out(row: SemanticLayer) -> SemanticLayerOut:
    spec = SemanticLayerSpec.model_validate(row.spec)
    return SemanticLayerOut(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        is_active=row.is_active,
        created_by=row.created_by,
        created_at=row.created_at,
        spec=spec,
        yaml=spec_to_yaml(spec),
    )


@router.post(
    "/generate",
    response_model=SemanticLayerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_app_access)],
    summary="Auto-generate a semantic layer (saved as a new active version)",
)
async def generate(
    project: ProjectDep, session: DbSession, generator: SemanticGenDep
) -> SemanticLayerOut:
    spec = await generator.generate(project.id, project_dialect(project))
    row = SemanticLayerRepository(session).save_new_version(project.id, spec, created_by="system")
    return _to_out(row)


@router.get("", response_model=SemanticLayerOut, summary="Get the semantic layer")
async def get_layer(
    project: ProjectDep,
    session: DbSession,
    version: int | None = Query(default=None),
) -> SemanticLayerOut:
    repo = SemanticLayerRepository(session)
    row = repo.get_version(project.id, version) if version else repo.get_active(project.id)
    if row is None:
        raise NotFoundError("No semantic layer for this project yet — generate one first")
    return _to_out(row)


@router.get("/versions", response_model=list[VersionMeta], summary="List versions")
async def list_versions(project: ProjectDep, session: DbSession) -> list[VersionMeta]:
    rows = SemanticLayerRepository(session).list_versions(project.id)
    return [VersionMeta.model_validate(r) for r in rows]


@router.put(
    "",
    response_model=SemanticLayerOut,
    dependencies=[Depends(verify_app_access)],
    summary="Save an edited semantic layer as a new active version",
)
async def update_layer(
    project: ProjectDep, body: SemanticLayerUpdate, session: DbSession
) -> SemanticLayerOut:
    spec = yaml_to_spec(body.yaml)  # raises 422 on invalid YAML/schema
    row = SemanticLayerRepository(session).save_new_version(project.id, spec, created_by="user")
    return _to_out(row)
