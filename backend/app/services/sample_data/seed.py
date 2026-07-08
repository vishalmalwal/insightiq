"""Seed the two sample projects (idempotent) + load their DuckDB data.

Touches both stores: metadata rows in Postgres, analytical tables in DuckDB.
Deterministic, so re-running produces identical data. Semantic layers for these
projects are added by the Phase 2 seed step.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.duckdb_manager import DuckDBManager
from app.db.models import Project
from app.repositories.data_sources import DataSourceRepository
from app.repositories.projects import ProjectRepository
from app.repositories.semantic_layers import SemanticLayerRepository
from app.services.ingestion.duckdb_ingest import IngestionService
from app.services.sample_data.generators import SAMPLE_DATASETS
from app.services.semantic_layer.generator import SemanticLayerGenerator

log = get_logger("insightiq.seed")


def seed_sample_data(session: Session, duckdb: DuckDBManager | None = None) -> list[Project]:
    duckdb = duckdb or DuckDBManager()
    projects_repo = ProjectRepository(session)
    ds_repo = DataSourceRepository(session)
    ingest = IngestionService(duckdb)
    generator = SemanticLayerGenerator(duckdb)
    sem_repo = SemanticLayerRepository(session)

    seeded: list[Project] = []
    for slug, (display_name, gen) in SAMPLE_DATASETS.items():
        project = projects_repo.get_by_slug(slug)
        if project is None:
            project = projects_repo.create(name=display_name, data_source="sample")
            project.slug = slug
            session.flush()
            ds_repo.create(project_id=project.id, kind="duckdb")

        frames = gen()
        tables = ingest.ingest_frames(project.id, frames)

        # Ready-made semantic layer (heuristic, deterministic) so the sample
        # projects demo end-to-end with zero setup. Only create v1 if absent.
        if sem_repo.get_active(project.id) is None:
            spec = generator.build(project.id, dialect="duckdb")
            sem_repo.save_new_version(project.id, spec, created_by="system")

        log.info(
            "seeded_project",
            slug=slug,
            tables=[t.name for t in tables],
            rows={t.name: t.row_count for t in tables},
        )
        seeded.append(project)

    session.commit()
    return seeded
