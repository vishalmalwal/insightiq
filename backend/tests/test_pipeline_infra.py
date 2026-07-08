"""Free-tier survival kit + executor: token bucket, backoff, cache, executor caps."""
from __future__ import annotations

import asyncio

import pytest

from app.db.duckdb_manager import DuckDBManager
from app.repositories.projects import ProjectRepository
from app.services.llm.errors import RateLimitError
from app.services.llm.rate_limiter import TokenBucket, retry_on_rate_limit
from app.services.pipeline.cache import ResponseCache
from app.services.pipeline.errors import ExecError
from app.services.pipeline.executor import DuckDBExecutor
from app.services.pipeline.guard import SqlGuard
from app.services.sample_data.seed import seed_sample_data


def test_token_bucket_limits_then_refills() -> None:
    clock = [0.0]

    async def fake_sleep(d: float) -> None:
        clock[0] += d

    async def scenario() -> None:
        tb = TokenBucket(rate_per_min=60, capacity=2, now=lambda: clock[0], sleep=fake_sleep)
        await tb.acquire()  # 2 -> 1
        await tb.acquire()  # 1 -> 0 (instant, no sleep)
        assert clock[0] == 0.0
        await tb.acquire()  # empty -> must wait ~1s (rate = 1/s)
        assert clock[0] >= 1.0

    asyncio.run(scenario())


def test_retry_on_rate_limit_backs_off_then_succeeds() -> None:
    sleeps: list[float] = []

    async def spy_sleep(d: float) -> None:
        sleeps.append(d)

    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("429")
        return "ok"

    result = asyncio.run(
        retry_on_rate_limit(flaky, retries=5, base_delay=0.5, sleep=spy_sleep)
    )
    assert result == "ok"
    assert sleeps == [0.5, 1.0]  # exponential backoff


def test_retry_on_rate_limit_gives_up() -> None:
    async def always() -> str:
        raise RateLimitError("429")

    async def spy(_: float) -> None:
        return None

    with pytest.raises(RateLimitError):
        asyncio.run(retry_on_rate_limit(always, retries=2, base_delay=0.01, sleep=spy))


def test_response_cache_roundtrip_and_key_stability(db_session) -> None:
    project = ProjectRepository(db_session).create(name="Cache", data_source="sample")
    cache = ResponseCache(db_session)
    k1 = ResponseCache.key(project.id, 1, "Monthly Revenue ")
    k2 = ResponseCache.key(project.id, 1, "monthly revenue")   # case/space-insensitive
    assert k1 == k2
    assert cache.get(k1) is None
    cache.set(k1, project.id, {"answer": 42})
    assert cache.get(k1) == {"answer": 42}
    # version change → different key
    assert ResponseCache.key(project.id, 2, "monthly revenue") != k1


def test_executor_runs_and_errors(db_session) -> None:
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    ex = DuckDBExecutor(DuckDBManager())

    cols, rows = ex.run(ecom.id, "SELECT status, COUNT(*) AS c FROM orders GROUP BY status")
    assert "status" in cols and len(rows) > 0

    with pytest.raises(ExecError):
        ex.run(ecom.id, "SELECT nonexistent_column FROM orders")


def test_executor_byte_cap_truncates(db_session) -> None:
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    ex = DuckDBExecutor(DuckDBManager())
    ex._max_bytes = 50  # force truncation
    guarded = SqlGuard(10000).validate("SELECT order_id FROM orders", ex_sem(), "duckdb")
    _, rows = ex.run(ecom.id, guarded)
    assert len(rows) < 1000  # capped well below the ~24k orders


def ex_sem():
    from app.schemas.semantic_layer import DataSourceSpec, Entity, SemanticLayerSpec

    return SemanticLayerSpec(
        data_source=DataSourceSpec(type="duckdb", dialect="duckdb"),
        entities=[Entity(name="orders", table="orders")],
    )
