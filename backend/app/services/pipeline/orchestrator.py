"""The ask pipeline: cache → plan → (build → guard → execute, with self-correction)
per intent → captions → persist dashboard. Planner 429s degrade gracefully.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, UnsafeSQLError
from app.core.logging import get_logger
from app.db.duckdb_manager import DuckDBManager
from app.db.models import AskRequest, Project
from app.db.models import LLMUsage as LLMUsageRow
from app.repositories.dashboards import DashboardRepository
from app.repositories.semantic_layers import SemanticLayerRepository
from app.schemas.pipeline import AnalysisIntent, AnalysisPlan, AskResponse, IntentCard
from app.schemas.semantic_layer import SemanticLayerSpec
from app.services.llm.errors import RateLimitError
from app.services.pipeline.cache import ResponseCache
from app.services.pipeline.errors import BuildError, ExecError
from app.services.pipeline.executor import DuckDBExecutor
from app.services.pipeline.guard import SqlGuard
from app.services.pipeline.planner import Planner
from app.services.pipeline.sql_builder import SqlBuilder

log = get_logger("insightiq.ask")

_DEGRADED_MSG = "High demand right now — try one of the sample questions in a moment."
_CAPTION_SYSTEM = "You write one concise, specific BI insight caption. No preamble, under 20 words."


class AskOrchestrator:
    def __init__(self, session: Session, duckdb: DuckDBManager | None = None) -> None:
        self._s = session
        self._duck = duckdb or DuckDBManager()
        self._planner = Planner()
        self._builder = SqlBuilder()
        self._guard = SqlGuard(get_settings().sql_row_limit)
        self._executor = DuckDBExecutor(self._duck)
        self._cache = ResponseCache(session)
        self._provider_name = get_settings().llm_provider
        self._can_repair = self._provider_name == "gemini"

    async def ask(
        self,
        project: Project,
        question: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> AskResponse:
        sem_row = SemanticLayerRepository(self._s).get_active(project.id)
        if sem_row is None:
            raise NotFoundError("No semantic layer for this project — generate one first")
        sem = SemanticLayerSpec.model_validate(sem_row.spec)
        dialect = sem.data_source.dialect
        date_range = (date_from, date_to) if date_from and date_to else None

        key = ResponseCache.key(project.id, sem.version, question, date_range)
        cached = self._cache.get(key)
        if cached is not None:
            resp = AskResponse.model_validate(cached)
            resp.cache_hit = True
            return resp

        try:
            plan, usage = await self._planner.plan(question, sem)
        except RateLimitError:
            log.warning("planner_rate_limited")
            return AskResponse(
                question=question,
                degraded=True,
                message=_DEGRADED_MSG,
                plan=AnalysisPlan(question=question, intents=[]),
            )

        cards = [
            await self._run_intent(project.id, it, sem, dialect, date_range) for it in plan.intents
        ]
        for card in cards:
            card.caption = await self._caption(card)
        cost = float(usage.cost_usd) if usage else 0.0

        ask_row = AskRequest(
            project_id=project.id,
            question=question,
            sem_version=sem.version,
            plan=plan.model_dump(),
            cache_hit=False,
            cost_usd=cost,
        )
        self._s.add(ask_row)
        self._s.flush()
        if usage:
            self._s.add(
                LLMUsageRow(
                    purpose="plan",
                    model=usage.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost_usd=usage.cost_usd,
                )
            )

        resp = AskResponse(
            ask_request_id=str(ask_row.id),
            question=question,
            cost_usd=cost,
            plan=plan,
            cards=cards,
        )

        # Persist an assembled dashboard so the result is shareable/reloadable.
        dash = DashboardRepository(self._s).create(ask_row.id, layout={}, charts={})
        resp.dashboard_id = str(dash.id)
        dash.charts = resp.model_dump(mode="json")

        self._cache.set(key, project.id, resp.model_dump(mode="json"))
        self._s.commit()
        return resp

    async def _run_intent(
        self,
        project_id: uuid.UUID,
        intent: AnalysisIntent,
        sem: SemanticLayerSpec,
        dialect: str,
        date_range: tuple[str, str] | None = None,
    ) -> IntentCard:
        prev_sql: str | None = None
        error: str | None = None

        for attempt in range(3):  # 1 initial + up to 2 self-correction retries
            try:
                sql = await self._generate_sql(intent, sem, dialect, error, prev_sql, date_range)
            except BuildError as exc:
                error = str(exc)
                break
            if attempt > 0 and sql == prev_sql:
                break
            try:
                guarded = self._guard.validate(sql, sem, dialect)
                columns, rows = self._executor.run(project_id, guarded)
                return IntentCard(
                    intent_id=intent.id,
                    type=intent.type,
                    title=intent.title,
                    ok=True,
                    sql=guarded,
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                )
            except (UnsafeSQLError, ExecError) as exc:
                error = str(exc)
                prev_sql = sql
                log.info("intent_retry", intent=intent.id, attempt=attempt, error=error)
                if not self._can_repair:
                    break

        return IntentCard(
            intent_id=intent.id,
            type=intent.type,
            title=intent.title,
            ok=False,
            error="Couldn't answer this part of the question.",
        )

    async def _generate_sql(
        self,
        intent: AnalysisIntent,
        sem: SemanticLayerSpec,
        dialect: str,
        error: str | None,
        prev_sql: str | None,
        date_range: tuple[str, str] | None = None,
    ) -> str:
        if error and prev_sql and self._can_repair:
            return await self._llm_repair(intent, sem, dialect, prev_sql, error)
        return self._builder.build(intent, sem, date_range)

    async def _caption(self, card: IntentCard) -> str | None:
        """One short insight caption via Flash-Lite. Skipped on mock; never fatal."""
        if self._provider_name != "gemini" or not card.ok or not card.rows:
            return None
        try:  # pragma: no cover - needs a live LLM
            from app.services.llm import get_llm_provider

            provider = get_llm_provider()
            prompt = (
                f"Chart: {card.title}\nColumns: {card.columns}\n"
                f"Rows (sample): {card.rows[:6]}\nWrite the caption."
            )
            result = await provider.complete(
                system=_CAPTION_SYSTEM,
                prompt=prompt,
                model=get_settings().llm_model_cheap,
                max_tokens=60,
            )
            return result.text.strip()[:200] or None
        except Exception as exc:  # noqa: BLE001 - a caption must never break a card
            log.warning("caption_failed", intent=card.intent_id, error=str(exc))
            return None

    async def _llm_repair(
        self, intent: AnalysisIntent, sem: SemanticLayerSpec, dialect: str, sql: str, error: str
    ) -> str:  # pragma: no cover - needs a live LLM
        from app.services.llm import get_llm_provider

        provider = get_llm_provider()
        system = (
            f"Fix this {dialect} SQL. It must be a single read-only SELECT using only "
            "tables/columns from the semantic layer. Return SQL only, no prose."
        )
        prompt = f"Error: {error}\n\nSQL:\n{sql}"
        result = await provider.complete(system=system, prompt=prompt)
        text = result.text.strip()
        return text.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
