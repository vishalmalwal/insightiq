"""Question → typed analysis plan.

Real path: Gemini structured output emits an `AnalysisPlan` directly (no
free-text parsing). Mock/CI path: a deterministic keyword planner maps the
question onto the semantic layer, so tests are stable and $0. Either way the plan
is validated against the semantic layer; invalid intents are dropped, and if the
LLM plan is unusable we fall back to the deterministic one.
"""
from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.pipeline import AnalysisIntent, AnalysisPlan
from app.schemas.semantic_layer import SemanticLayerSpec
from app.services.llm.base import LLMUsage

log = get_logger("insightiq.planner")

_PLANNER_SYSTEM = (
    "You are an analytics planner. Given a question and a semantic layer, produce "
    "1-6 analysis intents (trend/breakdown/comparison/kpi/distribution). Reference "
    "ONLY entities, measures, and dimensions that exist in the semantic layer. Use "
    "each entity's primary_time_dimension for time-based questions unless the user "
    "names a different date. Return a structured AnalysisPlan."
)

_GRAINS = {
    "daily": "day", "weekly": "week", "monthly": "month",
    "quarterly": "quarter", "yearly": "year", "annual": "year", "annually": "year",
}
_COMPARE_HINTS = (
    "vs", "versus", "compare", "comparison", "year over year", "year-over-year",
    "yoy", "last year", "previous year", "prior year",
)
_REVENUE_WORDS = ("revenue", "sales", "gmv", "turnover", "income")
_COUNT_WORDS = ("count", "many", "number")
_DISTRIBUTION_HINTS = ("share", "proportion", "split", "distribution", "composition", "mix")


def _measures(sem: SemanticLayerSpec) -> list[tuple[str, object]]:
    return [(e.name, m) for e in sem.entities for m in e.measures]


def _dims(sem: SemanticLayerSpec) -> list[tuple[str, object]]:
    return [(e.name, d) for e in sem.entities for d in e.dimensions]


def plan_deterministic(question: str, sem: SemanticLayerSpec) -> AnalysisPlan:
    q = question.lower()
    words = set(re.findall(r"[a-z0-9]+", q))
    measures = _measures(sem)
    dims = _dims(sem)
    if not measures:
        return AnalysisPlan(question=question, intents=[])

    def measure_score(item: tuple[str, object]) -> int:
        _, m = item
        n = m.name.lower()  # type: ignore[attr-defined]
        s = 0
        if m.format == "currency":  # type: ignore[attr-defined]
            s += 3
        if m.agg == "sum":  # type: ignore[attr-defined]
            s += 1
        if any(k in n for k in ("amount", "revenue", "sales", "mrr", "total")):
            s += 2
        if m.agg == "count_distinct":  # type: ignore[attr-defined]
            s -= 1
        return s

    primary = max(measures, key=measure_score)[1].name  # type: ignore[attr-defined]
    measure = primary
    if any(w in words for w in _COUNT_WORDS):
        cnt = next((m.name for _, m in measures if m.agg in ("count_distinct", "count")), None)  # type: ignore[attr-defined]
        if cnt:
            measure = cnt
    if "mrr" in words or "recurring" in q:
        mrr = next((m.name for _, m in measures if "mrr" in m.name.lower()), None)  # type: ignore[attr-defined]
        if mrr:
            measure = mrr
    base = next(en for en, m in measures if m.name == measure)  # type: ignore[attr-defined]

    def find_dim(term: str) -> str | None:
        for _, d in dims:
            if d.type in ("categorical", "boolean") and (  # type: ignore[attr-defined]
                d.name == term or d.name.replace("_", " ") == term or term in d.name  # type: ignore[attr-defined]
            ):
                return d.name  # type: ignore[attr-defined]
        return None

    breakdown = None
    for term in re.findall(r"by (\w+)", q):
        breakdown = find_dim(term)
        if breakdown:
            break
    if not breakdown:
        for _, d in dims:
            if d.type in ("categorical", "boolean") and d.name in words:  # type: ignore[attr-defined]
                breakdown = d.name  # type: ignore[attr-defined]
                break

    grain = None
    for w, g in _GRAINS.items():
        if w in q:
            grain = g
            break
    if not grain and ("over time" in q or "trend" in words or "per month" in q or "by month" in q):
        grain = "month"
    comparison = any(k in q for k in _COMPARE_HINTS)
    distribution = any(k in q for k in _DISTRIBUTION_HINTS)
    top_match = re.search(r"top\s+(\d+)?\s*(\w+)", q)

    intents: list[AnalysisIntent] = []

    def add(kind: str, title: str, **kw: object) -> None:
        intents.append(
            AnalysisIntent(
                id=f"i{len(intents) + 1}",
                type=kind,
                title=title,
                entity=base,
                measures=[measure],
                **kw,
            )
        )

    if comparison:
        title = f"{measure} over time" + (f" by {breakdown}" if breakdown else "")
        add(
            "comparison",
            f"{title} (period over period)",
            breakdown=breakdown,
            time_grain=grain or "year",
        )
    if grain and not comparison:
        add("trend", f"{measure} by {grain}", time_grain=grain)
    if distribution and breakdown and not comparison:
        add("distribution", f"{measure} share by {breakdown}", breakdown=breakdown)
    if breakdown and not comparison and not distribution:
        n = int(top_match.group(1)) if top_match and top_match.group(1) else 10
        add("breakdown", f"top {breakdown} by {measure}", breakdown=breakdown, limit=n)
    if top_match:
        noun = top_match.group(2)
        dim_for_noun = None
        for e in sem.entities:
            if e.name.startswith(noun) or noun.startswith(e.name.rstrip("s")):
                dim_for_noun = next(
                    (d.name for d in e.dimensions if d.type in ("categorical", "boolean")), None
                )
                if dim_for_noun:
                    break
        if not dim_for_noun:
            dim_for_noun = find_dim(noun)
        if dim_for_noun and dim_for_noun != breakdown:
            n = int(top_match.group(1)) if top_match.group(1) else 10
            add("breakdown", f"top {n} {noun} by {measure}", breakdown=dim_for_noun, limit=n)

    if not intents:
        add("kpi", f"total {measure}")
        first_cat = next(
            (d.name for _, d in dims if d.type in ("categorical", "boolean")), None  # type: ignore[attr-defined]
        )
        if first_cat:
            add("breakdown", f"{measure} by {first_cat}", breakdown=first_cat, limit=10)

    return AnalysisPlan(question=question, intents=intents[:6])


def _validate_intents(plan: AnalysisPlan, sem: SemanticLayerSpec) -> AnalysisPlan:
    entities = {e.name for e in sem.entities}
    measure_names = {m.name for e in sem.entities for m in e.measures}
    dim_names = {d.name for e in sem.entities for d in e.dimensions}
    time_names = {d.name for e in sem.entities for d in e.dimensions if d.type == "time"}

    valid: list[AnalysisIntent] = []
    for it in plan.intents:
        if it.entity not in entities:
            continue
        if any(m not in measure_names for m in it.measures):
            continue
        if it.breakdown and it.breakdown not in dim_names:
            continue
        if it.time_dimension and it.time_dimension not in time_names:
            continue
        valid.append(it)
    return AnalysisPlan(question=plan.question, intents=valid[:6])


class Planner:
    async def plan(
        self, question: str, sem: SemanticLayerSpec
    ) -> tuple[AnalysisPlan, LLMUsage | None]:
        if get_settings().llm_provider == "gemini":
            from app.services.llm import get_llm_provider

            provider = get_llm_provider()
            prompt = f"Question: {question}\n\nSemantic layer (YAML):\n{_compact_sem(sem)}"
            plan, usage = await provider.complete_structured(
                system=_PLANNER_SYSTEM, prompt=prompt, schema=AnalysisPlan
            )
            plan.question = question
            valid = _validate_intents(plan, sem)
            if valid.intents:
                return valid, usage
            log.warning("planner_llm_empty_after_validation_falling_back")
            return plan_deterministic(question, sem), usage

        return plan_deterministic(question, sem), None


def _compact_sem(sem: SemanticLayerSpec) -> str:
    from app.services.semantic_layer.yaml_io import spec_to_yaml

    return spec_to_yaml(sem)
