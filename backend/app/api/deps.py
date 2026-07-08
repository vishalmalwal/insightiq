"""Shared FastAPI dependencies: settings, DB session, project lookup, services."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.db.models import Project
from app.db.session import get_session
from app.repositories.projects import ProjectRepository
from app.services.ingestion.duckdb_ingest import IngestionService
from app.services.pipeline.orchestrator import AskOrchestrator
from app.services.profiling.profiler import ProfilingService
from app.services.semantic_layer.generator import SemanticLayerGenerator


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
DbSession = Annotated[Session, Depends(get_session)]


def get_project(project_id: Annotated[uuid.UUID, Path()], session: DbSession) -> Project:
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return project


ProjectDep = Annotated[Project, Depends(get_project)]


def project_dialect(project: Project) -> str:
    return "postgres" if project.data_source == "postgres" else "duckdb"


def get_ingestion_service() -> IngestionService:
    return IngestionService()


def get_profiling_service() -> ProfilingService:
    return ProfilingService()


def get_semantic_generator() -> SemanticLayerGenerator:
    return SemanticLayerGenerator()


def get_ask_orchestrator(session: DbSession) -> AskOrchestrator:
    return AskOrchestrator(session)


IngestionDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ProfilingDep = Annotated[ProfilingService, Depends(get_profiling_service)]
SemanticGenDep = Annotated[SemanticLayerGenerator, Depends(get_semantic_generator)]
AskOrchestratorDep = Annotated[AskOrchestrator, Depends(get_ask_orchestrator)]

