"""The ask endpoint: question → plan + per-intent result cards."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import AskOrchestratorDep, ProjectDep
from app.core.security import verify_app_access
from app.schemas.pipeline import AskRequestBody, AskResponse
from app.services.sample_data.questions import questions_for

router = APIRouter(prefix="/projects/{project_id}", tags=["ask"])


@router.post(
    "/ask",
    response_model=AskResponse,
    dependencies=[Depends(verify_app_access)],
    summary="Ask a question → plan + per-intent results",
)
async def ask(
    project: ProjectDep, body: AskRequestBody, orchestrator: AskOrchestratorDep
) -> AskResponse:
    return await orchestrator.ask(project, body.question, body.date_from, body.date_to)


@router.get("/sample-questions", response_model=list[str], summary="Curated demo questions")
async def sample_questions(project: ProjectDep) -> list[str]:
    return questions_for(project.slug)
