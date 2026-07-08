"""Compile an analysis intent into SQL — strictly from the semantic layer.

Only tables/columns/joins declared in the pinned semantic layer are ever
referenced. Time-based intents that don't name a date default to the entity's
primary event date (order_date), never signup/start (non-negotiable #2).
"""
from __future__ import annotations

from collections import defaultdict, deque

from app.schemas.pipeline import AnalysisIntent, IntentFilter
from app.schemas.semantic_layer import Dimension, Entity, Measure, SemanticLayerSpec
from app.services.pipeline.errors import BuildError
from app.services.semantic_layer.time_dims import time_dim_score

_AGG_SQL = {
    "sum": "SUM",
    "avg": "AVG",
    "count": "COUNT",
    "min": "MIN",
    "max": "MAX",
}
_DEFAULT_GRAIN = {"trend": "month", "comparison": "year"}


class SqlBuilder:
    def build(
        self,
        intent: AnalysisIntent,
        sem: SemanticLayerSpec,
        date_range: tuple[str, str] | None = None,
    ) -> str:
        entities = {e.name: e for e in sem.entities}
        base = entities.get(intent.entity)
        if base is None:
            raise BuildError(f"Unknown entity '{intent.entity}'")

        measure_owner: dict[str, tuple[str, Measure]] = {}
        dim_owner: dict[str, tuple[str, Dimension]] = {}
        for e in sem.entities:
            for m in e.measures:
                measure_owner.setdefault(m.name, (e.name, m))
                measure_owner[f"{e.name}.{m.name}"] = (e.name, m)
            for d in e.dimensions:
                dim_owner.setdefault(d.name, (e.name, d))
                dim_owner[f"{e.name}.{d.name}"] = (e.name, d)

        def resolve_measure(name: str) -> tuple[str, Measure]:
            # prefer the base entity's member on a bare name
            local = f"{base.name}.{name}"
            if local in measure_owner:
                return measure_owner[local]
            if name in measure_owner:
                return measure_owner[name]
            raise BuildError(f"Unknown measure '{name}'")

        def resolve_dim(name: str) -> tuple[str, Dimension]:
            local = f"{base.name}.{name}"
            if local in dim_owner:
                return dim_owner[local]
            if name in dim_owner:
                return dim_owner[name]
            raise BuildError(f"Unknown dimension '{name}'")

        needed: set[str] = {base.name}
        select_parts: list[str] = []
        group_parts: list[str] = []
        order_parts: list[str] = []

        # --- time grouping (trend / comparison) ---
        if intent.type in ("trend", "comparison"):
            t_owner, t_dim = self._resolve_time_dimension(intent, base, sem, entities)
            needed.add(t_owner)
            grain = intent.time_grain or _DEFAULT_GRAIN[intent.type]
            period = f"date_trunc('{grain}', {t_owner}.{t_dim.sql})"
            select_parts.append(f"{period} AS period")
            group_parts.append(period)
            order_parts.append("period")

        # --- breakdown dimension (breakdown / distribution / optional on comparison) ---
        if intent.breakdown and intent.type in ("breakdown", "distribution", "comparison"):
            d_owner, d = resolve_dim(intent.breakdown)
            needed.add(d_owner)
            expr = f"{d_owner}.{d.sql}"
            select_parts.append(f"{expr} AS {d.name}")
            group_parts.append(expr)

        # --- measures (default to a count measure if none requested) ---
        measures = intent.measures or self._default_measure(base)
        if not measures:
            raise BuildError(f"Entity '{base.name}' has no measures to aggregate")
        first_measure_alias = None
        for mname in measures:
            m_owner, m = resolve_measure(mname)
            needed.add(m_owner)
            if m.agg == "count_distinct":
                expr = f"COUNT(DISTINCT {m_owner}.{m.sql})"
            else:
                expr = f"{_AGG_SQL.get(m.agg, 'SUM')}({m_owner}.{m.sql})"
            select_parts.append(f"{expr} AS {m.name}")
            if first_measure_alias is None:
                first_measure_alias = m.name

        # --- filters ---
        where_parts: list[str] = []
        for f in intent.filters:
            d_owner, d = resolve_dim(f.dimension)
            needed.add(d_owner)
            where_parts.append(self._render_filter(f"{d_owner}.{d.sql}", f))

        # --- global date-range filter (best-effort; skipped if no time dim) ---
        if date_range is not None:
            try:
                t_owner, t_dim = self._resolve_time_dimension(intent, base, sem, entities)
                needed.add(t_owner)
                lo = self._lit(date_range[0])
                hi = self._lit(date_range[1])
                where_parts.append(f"{t_owner}.{t_dim.sql} BETWEEN {lo} AND {hi}")
            except BuildError:
                pass  # entity has no date to filter on — leave it unfiltered

        # --- ordering ---
        if intent.type in ("breakdown", "distribution") and first_measure_alias:
            order_parts.append(f"{first_measure_alias} DESC")

        # --- assemble ---
        from_clause = self._from_and_joins(base, needed, sem, entities)
        sql = f"SELECT {', '.join(select_parts)}\n{from_clause}"
        if where_parts:
            sql += "\nWHERE " + " AND ".join(where_parts)
        if group_parts:
            sql += "\nGROUP BY " + ", ".join(group_parts)
        if order_parts:
            sql += "\nORDER BY " + ", ".join(order_parts)
        if intent.type in ("breakdown", "distribution"):
            sql += f"\nLIMIT {intent.limit or 20}"
        return sql

    # ------------------------------------------------------------------ helpers

    def _default_measure(self, base: Entity) -> list[str]:
        for m in base.measures:
            if m.agg in ("count_distinct", "count"):
                return [m.name]
        return [base.measures[0].name] if base.measures else []

    def _resolve_time_dimension(
        self,
        intent: AnalysisIntent,
        base: Entity,
        sem: SemanticLayerSpec,
        entities: dict[str, Entity],
    ) -> tuple[str, Dimension]:
        if intent.time_dimension:
            for e in sem.entities:
                for d in e.dimensions:
                    if d.name == intent.time_dimension and d.type == "time":
                        return e.name, d
            raise BuildError(f"Unknown time dimension '{intent.time_dimension}'")

        # No date named → prefer the primary event date across reachable entities.
        reachable = self._reachable(base.name, sem)
        best: tuple[int, str, Dimension] | None = None
        for ename in reachable:
            e = entities[ename]
            for d in e.dimensions:
                if d.type != "time":
                    continue
                score = time_dim_score(d.name)
                if e.primary_time_dimension == d.name:
                    score += 3
                if ename == base.name:
                    score += 1
                cand = (score, ename, d)
                if best is None or cand[0] > best[0]:
                    best = cand
        if best is None:
            raise BuildError("No time dimension available for a time-based question")
        return best[1], best[2]

    def _adjacency(self, sem: SemanticLayerSpec) -> dict[str, list[tuple[str, str]]]:
        adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for e in sem.entities:
            for j in e.joins:
                adj[e.name].append((j.to, j.on))
                adj[j.to].append((e.name, j.on))
        return adj

    def _reachable(self, base: str, sem: SemanticLayerSpec) -> list[str]:
        adj = self._adjacency(sem)
        seen = [base]
        q = deque([base])
        while q:
            cur = q.popleft()
            for nbr, _ in adj[cur]:
                if nbr not in seen:
                    seen.append(nbr)
                    q.append(nbr)
        return seen

    def _from_and_joins(
        self,
        base: Entity,
        needed: set[str],
        sem: SemanticLayerSpec,
        entities: dict[str, Entity],
    ) -> str:
        adj = self._adjacency(sem)
        # BFS spanning tree from base; record parent edge (parent, on).
        parent: dict[str, tuple[str, str]] = {}
        q = deque([base.name])
        seen = {base.name}
        while q:
            cur = q.popleft()
            for nbr, on in adj[cur]:
                if nbr not in seen:
                    seen.add(nbr)
                    parent[nbr] = (cur, on)
                    q.append(nbr)

        # Collect edges on the path from base to each needed entity.
        edges: list[tuple[str, str]] = []  # (entity, on) in join order
        added: set[str] = set()

        def add_path(target: str) -> None:
            chain: list[str] = []
            node = target
            while node != base.name:
                if node not in parent:
                    raise BuildError(f"Cannot join '{target}' to '{base.name}'")
                chain.append(node)
                node = parent[node][0]
            for ent in reversed(chain):
                if ent not in added:
                    added.add(ent)
                    edges.append((ent, parent[ent][1]))

        for ent in needed:
            if ent != base.name:
                add_path(ent)

        clause = f"FROM {base.table} AS {base.name}"
        for ent, on in edges:
            clause += f"\nJOIN {entities[ent].table} AS {ent} ON {on}"
        return clause

    def _render_filter(self, col: str, f: IntentFilter) -> str:
        if f.op == "in" and isinstance(f.value, list):
            vals = ", ".join(self._lit(v) for v in f.value)
            return f"{col} IN ({vals})"
        if f.op == "between" and isinstance(f.value, list) and len(f.value) == 2:
            return f"{col} BETWEEN {self._lit(f.value[0])} AND {self._lit(f.value[1])}"
        return f"{col} {f.op} {self._lit(f.value)}"

    def _lit(self, value: object) -> str:
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        # Escape single quotes → safe string literal (defence-in-depth; the guard
        # also rejects multi-statement / injected SQL).
        return "'" + str(value).replace("'", "''") + "'"
