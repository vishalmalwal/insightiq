"""Free-tier survival kit: a token-bucket request queue + exponential backoff.

Sized to the Gemini free-tier RPM (config `llm_max_rpm`). The bucket smooths
bursts; `retry_on_rate_limit` handles transient 429s. Clock/sleep are injectable
so both are deterministically testable without real time.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.services.llm.errors import RateLimitError

T = TypeVar("T")


class TokenBucket:
    def __init__(
        self,
        rate_per_min: float,
        capacity: float | None = None,
        *,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._rate = rate_per_min / 60.0
        self._capacity = capacity if capacity is not None else float(rate_per_min)
        self._tokens = self._capacity
        self._now = now
        self._sleep = sleep
        self._updated = now()

    def _refill(self) -> None:
        t = self._now()
        self._tokens = min(self._capacity, self._tokens + (t - self._updated) * self._rate)
        self._updated = t

    @property
    def tokens(self) -> float:
        self._refill()
        return self._tokens

    async def acquire(self) -> None:
        self._refill()
        while self._tokens < 1:
            wait = (1 - self._tokens) / self._rate if self._rate > 0 else 0.01
            await self._sleep(wait)
            self._refill()
        self._tokens -= 1


async def retry_on_rate_limit(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 5,
    base_delay: float = 0.5,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Await `fn`, retrying on RateLimitError with exponential backoff."""
    for attempt in range(retries + 1):
        try:
            return await fn()
        except RateLimitError:
            if attempt == retries:
                raise
            await sleep(base_delay * (2**attempt))
    raise RuntimeError("unreachable")
