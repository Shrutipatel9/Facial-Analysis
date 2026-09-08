import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["text", "single_select", "multi_select", "yes_no"]


class ShowIfOut(BaseModel):
    question_id: str
    in_values: list[str]


class QuestionOut(BaseModel):
    id: str
    number: int
    text: str
    type: QuestionType
    options: list[str] | None = None
    required: bool
    show_if: ShowIfOut | None = None


class QuestionSetResponse(BaseModel):
    questions: list[QuestionOut]
    disclaimer_text: str


class SubmitQuestionnaireRequest(BaseModel):
    # Deliberately loose here -- text/single_select/yes_no answers are str,
    # multi_select answers are list[str], and per-question type/option/
    # required validation needs the QUESTIONS constant, so it happens in
    # questionnaire_service.submit_response, not at this schema layer (same
    # division of labor as ResetPasswordRequest delegating email-aware
    # password rules to the service layer once more context is available).
    answers: dict[str, str | list[str]] = Field(default_factory=dict)
    disclaimer_accepted: bool = False


class QuestionnaireResponseOut(BaseModel):
    id: uuid.UUID
    submitted_at: datetime

    model_config = {"from_attributes": True}


class QuestionnaireStatusResponse(BaseModel):
    completed: bool
