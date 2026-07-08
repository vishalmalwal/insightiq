"""Curated sample questions for the zero-setup demo (chips in the UI).

Chosen so the deterministic planner produces a varied, correct dashboard —
line, bar, grouped comparison, donut, and a KPI stat — with zero typing.
"""
from __future__ import annotations

SAMPLE_QUESTIONS: dict[str, list[str]] = {
    "sample-ecommerce": [
        "compare monthly revenue by region this year vs last year and show top products",
        "monthly revenue trend",
        "top categories by revenue",
        "revenue share by region",
    ],
    "sample-saas": [
        "monthly recurring revenue trend",
        "mrr by plan",
        "number of accounts by industry",
        "total mrr",
    ],
}


def questions_for(slug: str) -> list[str]:
    return SAMPLE_QUESTIONS.get(slug, [])
