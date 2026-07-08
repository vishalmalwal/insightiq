"""Deterministic synthetic sample datasets with *planted* analysis stories.

The seed is fixed so demos and evals are stable run-to-run. Planted hooks:

E-commerce (orders):
  * Seasonal spike     — order volume + revenue jump every Nov/Dec.
  * Weak segment       — Tier-2 cities dip sharply in Q3 (Jul–Sep): ~45% fewer
                         orders and ~25% lower value, so "why did revenue dip in
                         Tier-2 cities?" has a real answer.
SaaS (subscriptions):
  * Churn cliff        — a wave of churn clusters around ~90 days tenure.
  * Plan effect        — Basic churns far more than Pro/Enterprise.
  * Leading signal     — usage tapers in the weeks before a churn.

Data spans 2024-01 .. 2026-06 so "this year vs last year" comparisons work
relative to mid-2026.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

DATA_START = date(2024, 1, 1)
DATA_END = date(2026, 6, 30)

_REGIONS = ["North", "South", "East", "West"]
_TIERS = ["Tier-1", "Tier-2", "Tier-3"]
_SEGMENTS = ["Consumer", "SMB", "Enterprise"]
_CATEGORIES = [
    "Electronics", "Home & Kitchen", "Apparel", "Beauty",
    "Sports", "Books", "Toys", "Grocery",
]


def _month_starts(start: date, end: date) -> list[date]:
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(date(y, m, 1))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return months


def _seasonal_factor(month: int) -> float:
    # Planted holiday spike: Nov/Dec run well above a normal month so the
    # holiday-vs-baseline ratio lands ~2.3x (see test_planted_seasonal_spike).
    return {11: 2.0, 12: 2.4}.get(month, 1.0)


def generate_ecommerce(seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # --- customers ---
    n_cust = 2000
    tiers = rng.choice(_TIERS, size=n_cust, p=[0.35, 0.4, 0.25])
    customers = pd.DataFrame(
        {
            "customer_id": np.arange(1, n_cust + 1),
            "name": [f"Customer {i}" for i in range(1, n_cust + 1)],
            "region": rng.choice(_REGIONS, size=n_cust),
            "city_tier": tiers,
            "segment": rng.choice(_SEGMENTS, size=n_cust, p=[0.6, 0.3, 0.1]),
            "signup_date": [
                DATA_START + timedelta(days=int(d)) for d in rng.integers(0, 365, n_cust)
            ],
        }
    )
    tier_by_cust = dict(zip(customers["customer_id"], customers["city_tier"], strict=True))

    # --- products ---
    n_prod = 200
    prices = np.round(rng.lognormal(mean=3.2, sigma=0.6, size=n_prod) + 5, 2)
    products = pd.DataFrame(
        {
            "product_id": np.arange(1, n_prod + 1),
            "product_name": [f"Product {i}" for i in range(1, n_prod + 1)],
            "category": rng.choice(_CATEGORIES, size=n_prod),
            "unit_price": prices,
        }
    )
    price_by_prod = dict(zip(products["product_id"], products["unit_price"], strict=True))

    # --- orders (month by month, so seasonality + trend are explicit) ---
    months = _month_starts(DATA_START, DATA_END)
    order_rows = []
    next_order_id = 1
    for idx, mstart in enumerate(months):
        trend = 1.0 + 0.010 * idx
        noise = rng.normal(1.0, 0.05)
        n_orders = int(620 * trend * _seasonal_factor(mstart.month) * max(noise, 0.5))
        days_in_month = ((mstart.replace(day=28) + timedelta(days=4)).replace(day=1) - mstart).days
        for _ in range(n_orders):
            cust = int(rng.integers(1, n_cust + 1))
            day = int(rng.integers(0, days_in_month))
            odate = mstart + timedelta(days=day)
            tier = tier_by_cust[cust]

            # Planted: Tier-2 Q3 dip — drop ~45% of those orders outright.
            if tier == "Tier-2" and mstart.month in (7, 8, 9) and rng.random() < 0.45:
                continue
            amount_factor = 0.75 if (tier == "Tier-2" and mstart.month in (7, 8, 9)) else 1.0

            order_rows.append((next_order_id, cust, odate, "completed", amount_factor))
            next_order_id += 1

    orders_full = pd.DataFrame(
        order_rows, columns=["order_id", "customer_id", "order_date", "status", "_amt_factor"]
    )

    # --- order_items (vectorised via repeat) ---
    n_items_per = rng.integers(1, 5, size=len(orders_full))
    order_ids = np.repeat(orders_full["order_id"].to_numpy(), n_items_per)
    amt_factors = np.repeat(orders_full["_amt_factor"].to_numpy(), n_items_per)
    n_items = len(order_ids)
    prod_ids = rng.integers(1, n_prod + 1, size=n_items)
    quantities = rng.integers(1, 6, size=n_items)
    unit_prices = np.array([price_by_prod[p] for p in prod_ids])
    amounts = np.round(quantities * unit_prices * amt_factors, 2)
    order_items = pd.DataFrame(
        {
            "order_item_id": np.arange(1, n_items + 1),
            "order_id": order_ids,
            "product_id": prod_ids,
            "quantity": quantities,
            "unit_price": unit_prices,
            "amount": amounts,
        }
    )

    orders = orders_full.drop(columns=["_amt_factor"])
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
    }


_PLANS = ["Basic", "Pro", "Enterprise"]
_PLAN_MRR = {"Basic": 29.0, "Pro": 99.0, "Enterprise": 499.0}
_PLAN_CHURN = {"Basic": 0.55, "Pro": 0.28, "Enterprise": 0.14}
_INDUSTRIES = ["SaaS", "Fintech", "Retail", "Healthcare", "Media", "Manufacturing"]
_FEATURES = ["dashboard", "export", "api", "collaboration", "alerts"]


def generate_saas(seed: int = 43) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    n_acc = 1500
    span_days = (DATA_END - DATA_START).days - 30

    plans = rng.choice(_PLANS, size=n_acc, p=[0.55, 0.32, 0.13])
    signup_offsets = rng.integers(0, span_days, size=n_acc)
    signups = [DATA_START + timedelta(days=int(o)) for o in signup_offsets]
    seats = np.where(
        plans == "Enterprise",
        rng.integers(20, 200, n_acc),
        np.where(plans == "Pro", rng.integers(5, 30, n_acc), rng.integers(1, 6, n_acc)),
    )

    accounts = pd.DataFrame(
        {
            "account_id": np.arange(1, n_acc + 1),
            "company": [f"Acme {i}" for i in range(1, n_acc + 1)],
            "industry": rng.choice(_INDUSTRIES, size=n_acc),
            "country": rng.choice(["US", "UK", "DE", "IN", "BR", "AU"], size=n_acc),
            "plan": plans,
            "seats": seats,
            "signup_date": pd.to_datetime(signups),
        }
    )

    # --- subscriptions with the churn cliff ---
    sub_rows = []
    usage_rows = []
    next_usage_id = 1
    for i in range(n_acc):
        acc_id = i + 1
        plan = plans[i]
        start = signups[i]
        churns = rng.random() < _PLAN_CHURN[plan]
        end: date | None = None
        if churns:
            # Planted cliff: ~55% of churners leave right around day 90.
            if rng.random() < 0.55:
                tenure = int(np.clip(rng.normal(90, 8), 20, span_days))
            else:
                tenure = int(np.clip(rng.exponential(200), 20, span_days))
            churn_end = start + timedelta(days=tenure)
            if churn_end >= DATA_END:  # censored → still active
                churns = False
            else:
                end = churn_end

        status = "churned" if churns else "active"
        mrr = round(_PLAN_MRR[plan] * (1 + 0.05 * (seats[i] // 10)), 2)
        sub_rows.append((acc_id, acc_id, plan, mrr, start, end, status))

        # --- usage events (monthly), tapering before churn ---
        last = end if end is not None else DATA_END
        cursor = start
        while cursor < last:
            days_left = (last - cursor).days
            taper = 0.35 if (churns and days_left <= 30) else 1.0
            count = int(max(1, rng.poisson(20) * taper))
            usage_rows.append(
                (
                    next_usage_id,
                    acc_id,
                    pd.Timestamp(cursor),
                    rng.choice(_FEATURES),
                    count,
                )
            )
            next_usage_id += 1
            cursor = cursor + timedelta(days=30)

    subscriptions = pd.DataFrame(
        sub_rows,
        columns=[
            "subscription_id", "account_id", "plan", "mrr",
            "start_date", "end_date", "status",
        ],
    )
    subscriptions["start_date"] = pd.to_datetime(subscriptions["start_date"])
    subscriptions["end_date"] = pd.to_datetime(subscriptions["end_date"])

    usage_events = pd.DataFrame(
        usage_rows, columns=["event_id", "account_id", "event_date", "feature", "event_count"]
    )
    return {
        "accounts": accounts,
        "subscriptions": subscriptions,
        "usage_events": usage_events,
    }


SAMPLE_DATASETS = {
    "sample-ecommerce": ("E-commerce Orders (sample)", generate_ecommerce),
    "sample-saas": ("SaaS Subscriptions (sample)", generate_saas),
}
