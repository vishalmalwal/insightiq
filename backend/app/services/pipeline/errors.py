"""Pipeline error types."""
from __future__ import annotations

from app.core.errors import AppError


class BuildError(AppError):
    code = "sql_build_error"


class ExecError(AppError):
    code = "sql_exec_error"
