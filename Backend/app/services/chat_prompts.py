"""Suggested-prompt personalization (FR-019, Milestone 2 Phase 12) -- pure
function, no DB/AI dependency.

Per the user's explicit 2026-09-14 decision: computed deterministically
from the user's own already-assembled Report `sections` (Phase 10's
feature_scores/facial_assessments), not a new AI call -- same cost-
conscious posture as Phase 11's templated variation catalog. Degrades
gracefully (omits a personalized prompt) when its underlying data isn't
available, never fabricates one.
"""

from typing import Any

# Matches the two generic examples from docs/milestone2_requirements.md §2.4 verbatim.
_LEAD_PROMPT = "What are my top improvement priorities?"
_TAIL_PROMPT = "How should I track progress over 30 days?"


def build_suggested_prompts(sections: dict[str, Any]) -> list[str]:
    """Always includes the 2 generic prompts; includes up to 2 more
    personalized ones when the underlying data is available. Returns at
    most 4, matching FR-019's "3-4 suggested starter prompts" requirement."""
    prompts = [_LEAD_PROMPT]

    feature_scores = sections.get("feature_scores") or {}
    available_scores = [
        (feature, data["score"])
        for feature, data in feature_scores.items()
        if isinstance(data, dict) and data.get("available") and data.get("score") is not None
    ]
    if available_scores:
        lowest_feature = min(available_scores, key=lambda pair: pair[1])[0]
        prompts.append(f"What should I focus on for {lowest_feature}?")

    facial_assessments = sections.get("facial_assessments") or {}
    face_shape = facial_assessments.get("face_shape") or {}
    if face_shape.get("available") and face_shape.get("label"):
        prompts.append(f"Which hairstyle direction fits my {face_shape['label'].lower()} face shape?")

    prompts.append(_TAIL_PROMPT)
    return prompts
