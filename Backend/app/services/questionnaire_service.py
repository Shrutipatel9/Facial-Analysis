"""Onboarding questionnaire: the fixed 23-question flow + disclaimer gate
(FR-003, FR-004, BR-003). Content is verbatim from
docs/onboarding_questionnaire_spec.md (client-sourced, from the Qoves
reference recording) -- do not edit question text/options here without
updating that doc too.

This is a small, fixed, well-known question set, not a dynamic
content-managed system -- the only branching relationship is `show_if`
(one question, or a Yes-reveals-a-follow-up pair), evaluated by the single
`is_visible` function below. Do not grow this into a generic rule engine.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DisclaimerNotAcceptedError, QuestionnaireAnswersInvalidError
from app.models.questionnaire_response import QuestionnaireResponse

QuestionType = Literal["text", "single_select", "multi_select", "yes_no"]


@dataclass(frozen=True)
class ShowIf:
    question_id: str
    in_values: tuple[str, ...]


@dataclass(frozen=True)
class Question:
    id: str
    number: int  # display number, 1-23 -- follow-ups reuse their parent's number
    text: str
    type: QuestionType
    options: tuple[str, ...] | None = None
    required: bool = True
    show_if: ShowIf | None = None


# [Assumption, pending client confirmation -- docs/onboarding_questionnaire_spec.md §5]
# q9_details/q11_details: Yes on q9/q11 is assumed to reveal an optional
# free-text follow-up, rendered on the same wizard step as the parent
# question (see QuestionnaireWizard.tsx), not as a separate numbered step.
QUESTIONS: tuple[Question, ...] = (
    Question("q1", 1, "What is your occupation?", "text"),
    Question(
        "q2", 2, "How often do you smoke?", "single_select",
        options=("Never", "Rarely", "Sometimes", "Often", "Daily"),
    ),
    Question(
        "q3", 3, "How often do you drink?", "single_select",
        options=("Never", "Rarely", "Sometimes", "Often", "Daily"),
    ),
    Question(
        "q4", 4, "Would you rather look more masculine or more feminine?", "single_select",
        options=("Masculine", "Feminine", "No Preference"),
    ),
    Question("q5", 5, "Have you had any non-surgical aesthetic treatments before?", "yes_no", options=("Yes", "No")),
    Question(
        "q6", 6,
        "We're strictly non-surgical, but for accuracy, have you ever undergone facial cosmetic surgery?",
        "yes_no", options=("Yes", "No"),
    ),
    Question(
        "q7", 7, "Please select all treatment types you are comfortable undergoing", "multi_select",
        options=(
            "Injectables (Botox, Dermal Fillers, Fat-Dissolving Injections)",
            "Non-invasive (Laser, IPL/LED, Ultrasound, Radiofrequency)",
            "Invasive (Microneedling, Endo-Lift, Collagen-Stimulating Procedures)",
            "Semi-permanent (Microblading, Lip Blush, Tattoo-Based Treatments)",
        ),
    ),
    Question(
        "q8", 8, "Do you have any medical conditions (e.g. autoimmune disorders, diabetes)?",
        "yes_no", options=("Yes", "No"),
    ),
    Question("q9", 9, "Are you taking any medications (prescription or OTC)?", "yes_no", options=("Yes", "No")),
    Question(
        "q9_details", 9, "Please list your medications.", "text", required=False,
        show_if=ShowIf("q9", ("Yes",)),
    ),
    Question(
        "q10", 10, "Have you used retinoids (e.g. Isotretinoin/Accutane) in the past 6-12 months?",
        "yes_no", options=("Yes", "No"),
    ),
    Question(
        "q11", 11, "Do you have any allergies (skincare ingredients, lidocaine, latex, dyes)?",
        "yes_no", options=("Yes", "No"),
    ),
    Question(
        "q11_details", 11, "Please list your allergies.", "text", required=False,
        show_if=ShowIf("q11", ("Yes",)),
    ),
    Question(
        "q12", 12, "Any active infections, cold sores, or skin conditions (Rosacea, Eczema, Psoriasis)?",
        "yes_no", options=("Yes", "No"),
    ),
    Question("q13", 13, "Are you prone to hyperpigmentation?", "yes_no", options=("Yes", "No")),
    Question("q14", 14, "What feature do you like most about your face?", "text"),
    Question("q15", 15, "What feature do you dislike most about your face?", "text"),
    Question("q16", 16, "Are there any celebrities' facial aesthetics you'd like to look like?", "text"),
    Question("q17", 17, "Are you comfortable with weight loss recommendations?", "yes_no", options=("Yes", "No")),
    Question(
        "q18", 18, "What is your goal?", "single_select",
        options=(
            "Refine and enhance my facial aesthetic",
            "Significantly transform my facial aesthetic",
            "Undecided",
        ),
    ),
    # [Assumption, pending client confirmation] -- shown for q4 in
    # {Masculine, No Preference}, hidden only when q4 = Feminine.
    Question(
        "q19", 19, "Can you grow a full beard?", "yes_no", options=("Yes", "No"),
        show_if=ShowIf("q4", ("Masculine", "No Preference")),
    ),
    Question(
        "q20", 20, "How much distress does your current facial aesthetic cause you?", "single_select",
        options=(
            "No distress at all", "Minor distress", "Moderate distress",
            "Extreme distress and affects my day to day",
        ),
    ),
    Question(
        "q21", 21, "How often do you think about your appearance?", "single_select",
        options=(
            "Rarely (a few times a week or less)", "Occasionally (once a day)",
            "Frequently (multiple times a day)", "Very often (most of the day)",
            "Constantly (it's always on my mind)",
        ),
    ),
    Question("q22", 22, "What motivated you to sign up for FaceIQ?", "text"),
    Question("q23", 23, "Anything else you think we should know?", "text", required=False),
)

QUESTIONS_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}

DISCLAIMER_TEXT = (
    "I hereby confirm that I do not have any concerns related to Body Dysmorphic "
    "Disorder or other conditions affecting my perception of my appearance. I "
    "understand that treatment recommendations are purely for informational "
    "reasons and not medical guidance. Any implementation of treatments is at my "
    "own discretion."
)


def get_question_set() -> tuple[Question, ...]:
    return QUESTIONS


def is_visible(question: Question, answers: dict[str, Any]) -> bool:
    if question.show_if is None:
        return True
    return answers.get(question.show_if.question_id) in question.show_if.in_values


def _validate_and_clean(answers: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Recomputes each question's visibility from the answers themselves
    (the single source of truth is q4's/q9's/q11's value) rather than
    trusting any client-side visibility signal.

    - An unknown key (not a real question id) -> hard validation error.
    - A visible, required question missing/empty -> hard validation error.
    - A visible question whose value doesn't match its type/options -> hard
      validation error.
    - An answer present for a question that is NOT currently visible (e.g.
      q19 submitted alongside q4=Feminine, or q9_details submitted
      alongside q9=No) -> silently dropped, not rejected. A stale value
      left over from before the user changed an earlier answer is not the
      user's fault; rejecting the whole submission for it would be a
      confusing dead end. But it must not reach storage either -- answers
      later become OpenAI context (FR-008), and a value for a question the
      user was never actually shown would misrepresent them.
    """
    cleaned: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    unknown_keys = set(answers) - set(QUESTIONS_BY_ID)
    for key in unknown_keys:
        errors.append({"question_id": key, "reason": "Unknown question id."})

    for question in QUESTIONS:
        if not is_visible(question, answers):
            continue  # not currently visible -- any submitted value is silently dropped

        value = answers.get(question.id)
        is_empty = value is None or value == "" or value == []

        if is_empty:
            if question.required:
                errors.append({"question_id": question.id, "reason": "This question is required."})
            continue

        if question.type == "multi_select":
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                errors.append({"question_id": question.id, "reason": "Expected a list of selected options."})
                continue
            if question.options is not None and not set(value).issubset(question.options):
                errors.append({"question_id": question.id, "reason": "Contains an option that isn't allowed."})
                continue
        else:
            if not isinstance(value, str):
                errors.append({"question_id": question.id, "reason": "Expected a single text value."})
                continue
            if question.options is not None and value not in question.options:
                errors.append({"question_id": question.id, "reason": "Not one of the allowed options."})
                continue

        cleaned[question.id] = value

    return cleaned, errors


async def submit_response(
    db: AsyncSession, user_id: uuid.UUID, answers: dict[str, Any], disclaimer_accepted: bool
) -> QuestionnaireResponse:
    if not disclaimer_accepted:
        raise DisclaimerNotAcceptedError()

    cleaned, errors = _validate_and_clean(answers)
    if errors:
        raise QuestionnaireAnswersInvalidError(errors)

    record = QuestionnaireResponse(user_id=user_id, answers=cleaned, disclaimer_accepted=True)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def has_submitted(db: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await db.execute(select(QuestionnaireResponse.id).where(QuestionnaireResponse.user_id == user_id).limit(1))
    return result.scalar_one_or_none() is not None


async def get_latest_response(db: AsyncSession, user_id: uuid.UUID) -> QuestionnaireResponse | None:
    """Reused by facial-analysis-engine (Phase 4) -- there is no
    resubmission UI yet, so "latest" and "only" are equivalent today, but
    this is written to stay correct if that ever changes."""
    result = await db.execute(
        select(QuestionnaireResponse)
        .where(QuestionnaireResponse.user_id == user_id)
        .order_by(QuestionnaireResponse.submitted_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
