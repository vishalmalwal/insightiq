"""Auto-generate a semantic layer from table profiles.

Pipeline: profile every table → build a deterministic heuristic draft → (when a
real LLM is configured) enrich it via structured output. The heuristic draft is
always a valid fallback, so generation never hard-fails and CI/tests stay $0 on
the mock provider.
"""
from __future__ import annotations

import uuid

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.db.duckdb_manager import DuckDBManager
from app.schemas.data_sources import TableProfile
from app.schemas.semantic_layer import SemanticLayerSpec
from app.services.ingestion.duckdb_ingest import IngestionService
from app.services.profiling.profiler import ProfilingService
from app.services.semantic_layer.heuristics import build_heuristic_spec
from app.services.semantic_layer.yaml_io import spec_to_yaml

log = get_logger("insightiq.semantic")

_ENRICH_SYSTEM = (
    "You are a senior analytics engineer. You are given a DRAFT semantic layer and "
    "column profiles for a dataset. Improve it WITHOUT inventing tables or columns: "
    "keep every `table`, `sql`, and join `on` value exactly as given; only improve "
    "human-readable `description`s, add useful `synonyms`, set sensible measure "
    "`agg`/`format`, and add obvious derived `metrics` (e.g. average order value). "
    "Return the complete, valid semantic layer."
)


class SemanticLayerGenerator:
    def __init__(
        self,
        duckdb: DuckDBManager | None = None,
        profiling: ProfilingService | None = None,
        ingestion: IngestionService | None = None,
    ) -> None:
        self._duck = duckdb or DuckDBManager()
        self._profiling = profiling or ProfilingService(self._duck)
        self._ingestion = ingestion or IngestionService(self._duck)

    def _profiles(self, project_id: uuid.UUID) -> dict[str, TableProfile]:
        tables = self._ingestion.list_tables(project_id)
        return {t.name: self._profiling.profile_table(project_id, t.name) for t in tables}

    def build(self, project_id: uuid.UUID, dialect: str) -> SemanticLayerSpec:
        """Deterministic heuristic draft (no LLM). Used by the seeder + as fallback."""
        profiles = self._profiles(project_id)
        if not profiles:
            raise ValidationError("No tables found to build a semantic layer from")
        return build_heuristic_spec(profiles, dialect, str(project_id))

    async def generate(self, project_id: uuid.UUID, dialect: str) -> SemanticLayerSpec:
        """Heuristic draft, enriched by the LLM when a real provider is configured."""
        draft = self.build(project_id, dialect)
        if get_settings().llm_provider == "gemini":
            try:
                return await self._enrich(draft)
            except Exception as exc:  # noqa: BLE001 - fall back to the valid draft
                log.warning("semantic_enrich_failed", error=str(exc))
        return draft

    async def _enrich(self, draft: SemanticLayerSpec) -> SemanticLayerSpec:
        from app.services.llm import get_llm_provider

        provider = get_llm_provider()
        prompt = f"DRAFT semantic layer (YAML):\n\n{spec_to_yaml(draft)}"
        spec, _usage = await provider.complete_structured(
            system=_ENRICH_SYSTEM, prompt=prompt, schema=SemanticLayerSpec
        )
        # Never let the model change identity/version.
        spec.version = draft.version
        spec.project_id = draft.project_id
        return spec
