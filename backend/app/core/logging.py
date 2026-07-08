"""Structured logging with a per-request request_id (structlog)."""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    _request_id.set(rid)
    return rid


def bind_request_id(rid: str) -> None:
    _request_id.set(rid)


def _add_request_id(_: object, __: str, event_dict: dict) -> dict:
    event_dict["request_id"] = _request_id.get()
    return event_dict


def configure_logging(*, level: str = "INFO", json: bool = False) -> None:
    renderer = (
        structlog.processors.JSONRenderer()
        if json
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id,  # type: ignore[list-item]
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "insightiq") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
