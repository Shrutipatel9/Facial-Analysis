"""Onboarding questionnaire endpoints -- thin: all logic lives in
app/services/questionnaire_service.py. See
docs/onboarding_questionnaire_spec.md for the full question content.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.questionnaire import (
    QuestionnaireResponseOut,
    QuestionnaireStatusResponse,
    QuestionOut,
    QuestionSetResponse,
    ShowIfOut,
    SubmitQuestionnaireRequest,
)
from app.services import questionnaire_service

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


def _question_out(question: questionnaire_service.Question) -> QuestionOut:
    return QuestionOut(
        id=question.id,
        number=question.number,
        text=question.text,
        type=question.type,
        options=list(question.options) if question.options is not None else None,
        required=question.required,
        show_if=ShowIfOut(question_id=question.show_if.question_id, in_values=list(question.show_if.in_values))
        if question.show_if is not None
        else None,
    )


@router.get("", response_model=QuestionSetResponse)
async def get_questionnaire(user: User = Depends(get_current_user)) -> QuestionSetResponse:
    return QuestionSetResponse(
        questions=[_question_out(q) for q in questionnaire_service.get_question_set()],
        disclaimer_text=questionnaire_service.DISCLAIMER_TEXT,
    )


@router.get("/status", response_model=QuestionnaireStatusResponse)
async def get_questionnaire_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> QuestionnaireStatusResponse:
    completed = await questionnaire_service.has_submitted(db, user.id)
    return QuestionnaireStatusResponse(completed=completed)


@router.post("/responses", response_model=QuestionnaireResponseOut, status_code=status.HTTP_201_CREATED)
async def submit_questionnaire_response(
    payload: SubmitQuestionnaireRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionnaireResponseOut:
    record = await questionnaire_service.submit_response(
        db, user.id, payload.answers, payload.disclaimer_accepted
    )
    return QuestionnaireResponseOut.model_validate(record)
