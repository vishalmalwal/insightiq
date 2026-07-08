"""Seeding produces the two sample projects and the planted analysis stories."""
from __future__ import annotations

from app.db.duckdb_manager import DuckDBManager
from app.repositories.projects import ProjectRepository
from app.services.sample_data.seed import seed_sample_data


def test_seed_creates_projects_and_tables(db_session) -> None:
    projects = seed_sample_data(db_session, DuckDBManager())
    slugs = {p.slug for p in projects}
    assert slugs == {"sample-ecommerce", "sample-saas"}

    duck = DuckDBManager()
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    con = duck.connect(str(ecom.id), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        assert {"customers", "products", "orders", "order_items"} <= tables
        n_orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        assert n_orders > 20000
    finally:
        con.close()


def test_planted_seasonal_spike(db_session) -> None:
    """Holiday months (Nov+Dec) average >2x a non-holiday month, across the dataset.

    Canonical metric = avg holiday-month revenue / avg non-holiday-month revenue.
    Kept in lockstep with the ~2.3x claim in PROJECT_STATUS.
    """
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    con = DuckDBManager().connect(str(ecom.id), read_only=True)
    try:
        holiday_avg, non_holiday_avg = con.execute(
            """
            WITH monthly AS (
                SELECT date_trunc('month', o.order_date) AS ym,
                       month(o.order_date) AS m,
                       SUM(oi.amount) AS rev
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                GROUP BY 1, 2
            )
            SELECT AVG(CASE WHEN m IN (11, 12) THEN rev END),
                   AVG(CASE WHEN m NOT IN (11, 12) THEN rev END)
            FROM monthly
            """
        ).fetchone()
        assert holiday_avg / non_holiday_avg > 2.0
    finally:
        con.close()


def test_planted_tier2_q3_dip(db_session) -> None:
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    con = DuckDBManager().connect(str(ecom.id), read_only=True)
    try:
        q2, q3 = con.execute(
            """
            SELECT quarter(o.order_date) AS q, SUM(oi.amount) AS rev
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            JOIN order_items oi ON oi.order_id = o.order_id
            WHERE c.city_tier = 'Tier-2'
              AND year(o.order_date) = 2025
              AND quarter(o.order_date) IN (2, 3)
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
        # Tier-2 Q3 revenue is well below Q2 (planted dip).
        assert q3[1] < 0.7 * q2[1]
    finally:
        con.close()


def test_planted_churn_cliff(db_session) -> None:
    seed_sample_data(db_session, DuckDBManager())
    saas = ProjectRepository(db_session).get_by_slug("sample-saas")
    con = DuckDBManager().connect(str(saas.id), read_only=True)
    try:
        median_tenure = con.execute(
            """
            SELECT median(date_diff('day', start_date, end_date))
            FROM subscriptions WHERE status = 'churned'
            """
        ).fetchone()[0]
        assert 80 <= median_tenure <= 100          # cliff around ~90 days

        basic, enterprise = (
            con.execute(
                """
                SELECT plan, AVG(CASE WHEN status='churned' THEN 1.0 ELSE 0 END) AS churn
                FROM subscriptions WHERE plan IN ('Basic','Enterprise')
                GROUP BY plan ORDER BY plan
                """
            ).fetchall()
        )
        assert basic[1] > enterprise[1]            # Basic churns more
    finally:
        con.close()
