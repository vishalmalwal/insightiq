"""Build a solid draft semantic layer straight from table profiles.

Deterministic and dependency-free, so it works with the mock provider (tests/CI,
$0) and as a guaranteed fallback if the LLM step fails. The LLM path enriches
this draft (better names, descriptions, synonyms, derived metrics).
"""
from __future__ import annotations

from app.schemas.data_sources import TableProfile
from app.schemas.semantic_layer import (
    AggType,
    DataSourceSpec,
    Dimension,
    Entity,
    FormatType,
    Join,
    Measure,
    SemanticLayerSpec,
)
from app.services.semantic_layer.time_dims import pick_primary_time_dim

_CURRENCY_HINTS = ("price", "amount", "revenue", "mrr", "sales", "cost", "total", "spend")
_PERCENT_HINTS = ("pct", "percent", "rate", "ratio")
_AVG_HINTS = ("price", "rate", "ratio", "avg", "average", "pct", "percent", "score")


def _default_agg(name: str) -> AggType:
    n = name.lower()
    return "avg" if any(h in n for h in _AVG_HINTS) else "sum"


def _default_format(name: str) -> FormatType:
    n = name.lower()
    if any(h in n for h in _CURRENCY_HINTS):
        return "currency"
    if any(h in n for h in _PERCENT_HINTS):
        return "percent"
    return "number"


def _is_key(col_name: str) -> bool:
    return col_name.lower().endswith("_id") or col_name.lower() == "id"


def _find_primary_key(profile: TableProfile) -> list[str]:
    for col in profile.columns:
        if _is_key(col.name) and col.distinct_count == profile.row_count and profile.row_count > 0:
            return [col.name]
    return []


def build_heuristic_spec(
    profiles: dict[str, TableProfile], dialect: str, project_id: str | None = None
) -> SemanticLayerSpec:
    dia = "postgres" if dialect == "postgres" else "duckdb"

    # First pass: primary keys, so joins can be resolved in the second pass.
    pk_by_table = {name: _find_primary_key(p) for name, p in profiles.items()}
    pk_col_to_table = {
        pk[0]: name for name, pk in pk_by_table.items() if pk
    }

    entities: list[Entity] = []
    for table, profile in profiles.items():
        pk = pk_by_table[table]
        dimensions: list[Dimension] = []
        measures: list[Measure] = []
        joins: list[Join] = []

        for col in profile.columns:
            is_pk = col.name in pk
            if _is_key(col.name):
                # Resolve foreign keys to joins; keys are never measures/dimensions.
                if not is_pk and col.name in pk_col_to_table:
                    target = pk_col_to_table[col.name]
                    if target != table:
                        joins.append(
                            Join(
                                to=target,
                                type="many_to_one",
                                on=f"{table}.{col.name} = {target}.{col.name}",
                            )
                        )
                continue

            if col.semantic_type == "numeric":
                measures.append(
                    Measure(
                        name=col.name,
                        agg=_default_agg(col.name),
                        sql=col.name,
                        format=_default_format(col.name),
                    )
                )
            elif col.semantic_type in ("categorical", "boolean"):
                dimensions.append(
                    Dimension(
                        name=col.name,
                        type=col.semantic_type,
                        sql=col.name,
                    )
                )
            elif col.semantic_type == "time":
                dimensions.append(
                    Dimension(name=col.name, type="time", grain="day", sql=col.name)
                )
            # 'text' columns are neither measures nor dimensions by default.

        # A count measure keyed on the primary key is almost always wanted.
        if pk:
            measures.insert(
                0,
                Measure(
                    name=f"{table}_count",
                    agg="count_distinct",
                    sql=pk[0],
                    format="number",
                    description=f"Number of {table}.",
                ),
            )

        time_dims = [d.name for d in dimensions if d.type == "time"]
        entities.append(
            Entity(
                name=table,
                table=table,
                description=f"One row per {table[:-1] if table.endswith('s') else table}.",
                primary_key=pk,
                primary_time_dimension=pick_primary_time_dim(time_dims),
                dimensions=dimensions,
                measures=measures,
                joins=joins,
            )
        )

    return SemanticLayerSpec(
        version=1,
        project_id=project_id,
        data_source=DataSourceSpec(type=dia, dialect=dia),
        entities=entities,
        metrics=[],
    )
