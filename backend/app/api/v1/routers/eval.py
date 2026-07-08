"""Eval suite: run it and browse run history (the SQL-accuracy scoreboard)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.core.errors import NotFoundError
from app.core.security import verify_app_access
from app.repositories.eval import EvalRepository
from app.schemas.eval import EvalCaseResultOut, EvalRunDetail, EvalRunOut
from app.services.eval.harness import run_suite

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run", response_model=EvalRunOut, dependencies=[Depends(verify_app_access)])
async def run(session: DbSession) -> EvalRunOut:
    await run_suite(session)
    # Return the freshly finalized run (most recent).
    latest = EvalRepository(session).list_runs(limit=1)[0]
    return EvalRunOut.model_validate(latest)


@router.get("/runs", response_model=list[EvalRunOut])
async def list_runs(session: DbSession) -> list[EvalRunOut]:
    return [EvalRunOut.model_validate(r) for r in EvalRepository(session).list_runs()]


@router.get("/runs/{run_id}", response_model=EvalRunDetail)
async def get_run(run_id: uuid.UUID, session: DbSession) -> EvalRunDetail:
    repo = EvalRepository(session)
    run_row = repo.get_run(run_id)
    if run_row is None:
        raise NotFoundError(f"Eval run {run_id} not found")
    detail = EvalRunDetail.model_validate(run_row)
    detail.cases = [EvalCaseResultOut.model_validate(c) for c in repo.case_results(run_id)]
    return detail
