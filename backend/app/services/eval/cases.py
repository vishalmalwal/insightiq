"""Versioned eval suite: (question -> gold SQL) cases over the sample datasets.

Gold SQL is an independent, hand-written reference query. Execution accuracy is a
denotation match: does any card the pipeline produced return the same result set
as the gold query? A handful of cases are deliberately HARD (ambiguous time
dimension, multi-filter, top-N, period-over-period, unanswerable) -- the
deterministic planner is expected to miss some of these, which is the point: a
suite that can't drop below 100% isn't measuring anything. Bump SUITE_VERSION
whenever cases change.
"""
from __future__ import annotations

from dataclasses import dataclass

SUITE_VERSION = "2026.07-2"


@dataclass(frozen=True)
class EvalCase:
    id: str
    project_slug: str
    question: str
    gold_sql: str = ""                 # empty when expect_no_answer
    expect_intent: str | None = None
    expect_no_answer: bool = False     # correct behaviour = produce no answer
    hard: bool = False                 # deliberately hard/ambiguous


# gold-SQL FROM/JOIN building blocks
_OI = "order_items oi"
_OI_ORD = "order_items oi JOIN orders o ON oi.order_id = o.order_id"
_OI_ORD_CUST = _OI_ORD + " JOIN customers c ON o.customer_id = c.customer_id"
_OI_PROD = "order_items oi JOIN products p ON oi.product_id = p.product_id"
_SUB_ACC = "subscriptions s JOIN accounts a ON s.account_id = a.account_id"

ECOM = "sample-ecommerce"
SAAS = "sample-saas"

CASES: list[EvalCase] = [
    # =========================== e-commerce (clear) ===========================
    EvalCase(
        "ecom_revenue_trend", ECOM, "monthly revenue trend", expect_intent="trend",
        gold_sql=(
            f"SELECT date_trunc('month', o.order_date), SUM(oi.amount) "
            f"FROM {_OI_ORD} GROUP BY 1"
        ),
    ),
    EvalCase(
        "ecom_revenue_quarterly", ECOM, "quarterly revenue trend", expect_intent="trend",
        gold_sql=(
            f"SELECT date_trunc('quarter', o.order_date), SUM(oi.amount) "
            f"FROM {_OI_ORD} GROUP BY 1"
        ),
    ),
    EvalCase(
        "ecom_revenue_weekly", ECOM, "weekly revenue trend", expect_intent="trend",
        gold_sql=(
            f"SELECT date_trunc('week', o.order_date), SUM(oi.amount) "
            f"FROM {_OI_ORD} GROUP BY 1"
        ),
    ),
    EvalCase(
        "ecom_revenue_by_region", ECOM, "revenue by region", expect_intent="breakdown",
        gold_sql=f"SELECT c.region, SUM(oi.amount) FROM {_OI_ORD_CUST} GROUP BY 1",
    ),
    EvalCase(
        "ecom_revenue_by_category", ECOM, "revenue by category", expect_intent="breakdown",
        gold_sql=f"SELECT p.category, SUM(oi.amount) FROM {_OI_PROD} GROUP BY 1",
    ),
    EvalCase(
        "ecom_revenue_by_segment", ECOM, "revenue by segment", expect_intent="breakdown",
        gold_sql=f"SELECT c.segment, SUM(oi.amount) FROM {_OI_ORD_CUST} GROUP BY 1",
    ),
    EvalCase(
        "ecom_revenue_by_city_tier", ECOM, "revenue by city tier", expect_intent="breakdown",
        gold_sql=f"SELECT c.city_tier, SUM(oi.amount) FROM {_OI_ORD_CUST} GROUP BY 1",
    ),
    EvalCase(
        "ecom_total_revenue", ECOM, "total revenue", expect_intent="kpi",
        gold_sql=f"SELECT SUM(oi.amount) FROM {_OI}",
    ),
    EvalCase(
        "ecom_num_customers", ECOM, "number of customers", expect_intent="kpi",
        gold_sql="SELECT COUNT(DISTINCT customer_id) FROM customers",
    ),
    EvalCase(
        "ecom_customers_by_region", ECOM, "number of customers by region",
        expect_intent="breakdown",
        gold_sql="SELECT region, COUNT(DISTINCT customer_id) FROM customers GROUP BY 1",
    ),
    EvalCase(
        "ecom_customers_by_segment", ECOM, "number of customers by segment",
        expect_intent="breakdown",
        gold_sql="SELECT segment, COUNT(DISTINCT customer_id) FROM customers GROUP BY 1",
    ),
    EvalCase(
        "ecom_customers_by_city_tier", ECOM, "number of customers by city tier",
        expect_intent="breakdown",
        gold_sql="SELECT city_tier, COUNT(DISTINCT customer_id) FROM customers GROUP BY 1",
    ),
    EvalCase(
        "ecom_compare_region_years", ECOM, "compare revenue by region across years",
        expect_intent="comparison",
        gold_sql=(
            f"SELECT date_trunc('year', o.order_date), c.region, SUM(oi.amount) "
            f"FROM {_OI_ORD_CUST} GROUP BY 1, 2"
        ),
    ),
    EvalCase(
        "ecom_revenue_share_category", ECOM, "revenue share by category",
        expect_intent="distribution",
        gold_sql=f"SELECT p.category, SUM(oi.amount) FROM {_OI_PROD} GROUP BY 1",
    ),
    # ============================ e-commerce (hard) ===========================
    EvalCase(
        "ecom_signups_per_month", ECOM, "number of signups per month", hard=True,
        gold_sql=(
            "SELECT date_trunc('month', signup_date), COUNT(DISTINCT customer_id) "
            "FROM customers GROUP BY 1"
        ),
    ),
    EvalCase(
        "ecom_revenue_north_electronics", ECOM,
        "revenue in the North region for Electronics", hard=True,
        gold_sql=(
            f"SELECT SUM(oi.amount) FROM {_OI_ORD_CUST} "
            "JOIN products p ON oi.product_id = p.product_id "
            "WHERE c.region = 'North' AND p.category = 'Electronics'"
        ),
    ),
    EvalCase(
        "ecom_revenue_yoy", ECOM, "revenue this year versus last year", hard=True,
        gold_sql=(
            f"SELECT date_trunc('year', o.order_date), SUM(oi.amount) FROM {_OI_ORD} "
            "WHERE o.order_date >= DATE '2025-01-01' GROUP BY 1"
        ),
    ),
    EvalCase(
        "ecom_top3_products", ECOM, "top 3 products by revenue", hard=True,
        gold_sql=(
            f"SELECT p.product_name, SUM(oi.amount) FROM {_OI_PROD} "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 3"
        ),
    ),
    # =============================== saas (clear) =============================
    EvalCase(
        "saas_mrr_by_plan", SAAS, "mrr by plan", expect_intent="breakdown",
        gold_sql=f"SELECT a.plan, SUM(s.mrr) FROM {_SUB_ACC} GROUP BY 1",
    ),
    EvalCase(
        "saas_mrr_by_status", SAAS, "mrr by status", expect_intent="breakdown",
        gold_sql="SELECT status, SUM(mrr) FROM subscriptions GROUP BY 1",
    ),
    EvalCase(
        "saas_mrr_by_industry", SAAS, "mrr by industry", expect_intent="breakdown",
        gold_sql=f"SELECT a.industry, SUM(s.mrr) FROM {_SUB_ACC} GROUP BY 1",
    ),
    EvalCase(
        "saas_mrr_by_country", SAAS, "mrr by country", expect_intent="breakdown",
        gold_sql=f"SELECT a.country, SUM(s.mrr) FROM {_SUB_ACC} GROUP BY 1",
    ),
    EvalCase(
        "saas_total_mrr", SAAS, "total mrr", expect_intent="kpi",
        gold_sql="SELECT SUM(mrr) FROM subscriptions",
    ),
    EvalCase(
        "saas_num_accounts", SAAS, "number of accounts", expect_intent="kpi",
        gold_sql="SELECT COUNT(DISTINCT account_id) FROM accounts",
    ),
    EvalCase(
        "saas_accounts_by_industry", SAAS, "number of accounts by industry",
        expect_intent="breakdown",
        gold_sql="SELECT industry, COUNT(DISTINCT account_id) FROM accounts GROUP BY 1",
    ),
    EvalCase(
        "saas_accounts_by_country", SAAS, "number of accounts by country",
        expect_intent="breakdown",
        gold_sql="SELECT country, COUNT(DISTINCT account_id) FROM accounts GROUP BY 1",
    ),
    EvalCase(
        "saas_accounts_by_plan", SAAS, "number of accounts by plan", expect_intent="breakdown",
        gold_sql="SELECT plan, COUNT(DISTINCT account_id) FROM accounts GROUP BY 1",
    ),
    # ================================ saas (hard) =============================
    EvalCase(
        "saas_usage_by_feature", SAAS, "usage events by feature", hard=True,
        gold_sql="SELECT feature, SUM(event_count) FROM usage_events GROUP BY 1",
    ),
    EvalCase(
        "saas_mrr_enterprise_us", SAAS, "mrr for Enterprise accounts in the US", hard=True,
        gold_sql=(
            f"SELECT SUM(s.mrr) FROM {_SUB_ACC} "
            "WHERE a.plan = 'Enterprise' AND a.country = 'US'"
        ),
    ),
    EvalCase(
        "saas_churn_rate_by_plan", SAAS, "churn rate by plan", hard=True, expect_no_answer=True,
    ),
]
