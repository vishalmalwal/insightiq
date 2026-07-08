"""Rank time dimensions so revenue-style questions default to the event date
(order_date), never signup/start/end. Used by the heuristic generator and by the
SQL builder's default-time-dimension resolution.
"""
from __future__ import annotations

_EVENT_HINTS = (
    "order", "event", "transaction", "txn", "purchase", "sale", "invoice",
    "created", "booked", "placed", "occurred", "activity", "usage", "ship",
)
_NON_EVENT_HINTS = (
    "signup", "sign_up", "registration", "register", "start", "end", "expire",
    "expiry", "cancel", "churn", "updated", "modified", "birth", "dob", "renew",
)


def time_dim_score(name: str) -> int:
    n = name.lower()
    score = 0
    if any(h in n for h in _EVENT_HINTS):
        score += 2
    if n.endswith("_date") or n.endswith("_at") or n == "date":
        score += 1
    if any(h in n for h in _NON_EVENT_HINTS):
        score -= 3
    return score


def pick_primary_time_dim(names: list[str]) -> str | None:
    """Highest-scoring event-like date; shorter name breaks ties. None if empty."""
    if not names:
        return None
    return max(names, key=lambda x: (time_dim_score(x), -len(x)))
