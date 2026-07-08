"""Defense-in-depth SQL guard (DESIGN §7).

Every generated statement passes through here before execution:
parse (sqlglot) → single-statement → SELECT-only → table allowlist against the
pinned semantic layer → keyword denylist → auto-LIMIT injection. Any failure
raises UnsafeSQLError and the statement never reaches the database.
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

from app.core.errors import UnsafeSQLError
from app.schemas.semantic_layer import SemanticLayerSpec

# Statement/command node types that must never appear anywhere in the tree.
_FORBIDDEN_NODES = {
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "TruncateTable",
    "Command", "Copy", "Pragma", "Attach", "Detach", "Set", "Use", "Call",
    "LoadData", "Grant", "Merge",
}

# Belt-and-braces token denylist (case-insensitive, word-boundary).
_DENY_TOKENS = (
    "COPY", "ATTACH", "DETACH", "INSTALL", "LOAD", "PRAGMA", "INTO",
    "EXPORT", "IMPORT",
)
_DENY_RE = re.compile(r"\b(" + "|".join(_DENY_TOKENS) + r")\b", re.IGNORECASE)


class SqlGuard:
    def __init__(self, row_limit: int) -> None:
        self._row_limit = row_limit

    def validate(self, sql: str, sem: SemanticLayerSpec, dialect: str) -> str:
        # 1) token denylist first — cheap, catches things even if parsing is lenient
        if _DENY_RE.search(sql):
            raise UnsafeSQLError("Query contains a disallowed keyword")

        # 2) parse; must be exactly one statement
        try:
            statements = sqlglot.parse(sql, read=dialect)
        except Exception as exc:  # noqa: BLE001
            raise UnsafeSQLError(f"Could not parse SQL: {exc}") from exc
        statements = [s for s in statements if s is not None]
        if len(statements) != 1:
            raise UnsafeSQLError("Only a single statement is allowed")
        root = statements[0]

        # 3) must be a read query
        if not isinstance(root, (exp.Select, exp.Union, exp.Subquery)):
            raise UnsafeSQLError("Only SELECT statements are allowed")

        # 4) no forbidden node anywhere
        for node in root.walk():
            if type(node).__name__ in _FORBIDDEN_NODES:
                raise UnsafeSQLError(f"Disallowed operation: {type(node).__name__}")

        # 5) table allowlist against the pinned semantic layer
        allowed = {e.table.lower() for e in sem.entities}
        cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
        for table in root.find_all(exp.Table):
            name = table.name.lower()
            if name in cte_names:
                continue
            if name not in allowed:
                raise UnsafeSQLError(f"Table '{table.name}' is not in the semantic layer")

        # 6) auto-LIMIT injection (row cap defence-in-depth)
        if root.find(exp.Limit) is None:
            if isinstance(root, exp.Select):
                root = root.limit(self._row_limit)
            else:
                root = exp.select("*").from_(root.subquery("_capped")).limit(self._row_limit)

        return root.sql(dialect=dialect)
