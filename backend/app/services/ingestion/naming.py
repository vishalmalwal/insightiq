"""Turn arbitrary file/sheet names into safe SQL identifiers."""
from __future__ import annotations

import re


def safe_identifier(raw: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", raw.strip().lower()).strip("_")
    if not s:
        s = "table"
    if s[0].isdigit():
        s = f"t_{s}"
    return s[:63]
