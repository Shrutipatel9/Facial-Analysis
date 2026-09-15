"""Deterministic medical/medication-question refusal filter (FR-019,
Milestone 2 Phase 12) -- pure function, no DB/AI dependency.

Per the user's explicit 2026-09-14 decision (see
D:\\zzz\\chat-assistant\\plans.md decision 3): FR-019's "hard behavioral
rule, not optional" refusal requirement is enforced by intercepting an
obviously medical/medication question BEFORE any AI call, not left to the
model's system-prompt compliance alone -- real AI calls never run in tests
(BR-006), so an LLM's actual refusal behavior can't be verified in CI; a
deterministic keyword filter is the only way to make this literally,
testably true. The system prompt in chat_service.py separately instructs
refusal as defense-in-depth for anything this filter misses.

First-pass heuristic, same posture as ASM-007's recommendation-tiering
keyword list -- some false-positive risk on borderline phrasing (e.g. a
term used non-medically) is an accepted, intentional tradeoff: over-
refusing a borderline question is safer than under-refusing a real one.
Deliberately excludes bare "diagnose"/"diagnosis" as standalone verbs where
a legitimate report question could plausibly use them (e.g. "can you
diagnose my face shape") -- only the more specific "diagnose me" phrasing
is treated as medical.
"""

import re

_MEDICAL_TERMS: tuple[str, ...] = (
    "minoxidil",
    "retinoid",
    "retin-a",
    "tretinoin",
    "isotretinoin",
    "accutane",
    "finasteride",
    "spironolactone",
    "hydroquinone",
    "corticosteroid",
    "steroid",
    "antibiotic",
    "prescription",
    "prescribe",
    "dosage",
    "medication",
    "diagnose me",
    "side effect",
    "side effects",
    "contraindication",
    "overdose",
    "drug interaction",
    "is it safe to take",
    "how much should i take",
)

# Word-boundary match, not a plain substring check -- avoids false
# positives like "drug" matching inside "drugstore" or "steroid" matching
# inside a longer unrelated word.
_PATTERN = re.compile(r"\b(" + "|".join(re.escape(term) for term in _MEDICAL_TERMS) + r")\b", re.IGNORECASE)

REFUSAL_MESSAGE = (
    "I'm not able to advise on medications, dosages, prescriptions, or medical treatments -- "
    "that's outside what I can safely help with here. Please speak with a licensed dermatologist "
    "or other qualified professional about this. I'm happy to help with general, non-clinical "
    "questions about your report though!"
)


def is_medical_question(text: str) -> bool:
    return bool(_PATTERN.search(text))
