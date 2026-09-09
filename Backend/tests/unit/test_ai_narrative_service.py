from app.services.ai_narrative_service import _SYSTEM_PROMPT, _format_questionnaire_context
from app.services.questionnaire_service import QUESTIONS_BY_ID


class TestFormatQuestionnaireContext:
    def test_pairs_each_answer_with_its_real_question_text(self):
        answers = {"q4": "Masculine", "q14": "My eyes", "q18": "Undecided"}
        context = _format_questionnaire_context(answers)

        assert f"{QUESTIONS_BY_ID['q4'].text}: Masculine" in context
        assert f"{QUESTIONS_BY_ID['q14'].text}: My eyes" in context
        assert f"{QUESTIONS_BY_ID['q18'].text}: Undecided" in context

    def test_never_emits_raw_opaque_question_ids(self):
        # The whole point of this function is that the AI never sees a bare
        # "q15" -- only the real question text -- so a raw key must never
        # appear as its own line.
        answers = {"q15": "My nose"}
        context = _format_questionnaire_context(answers)
        assert "q15:" not in context
        assert "My nose" in context

    def test_skips_blank_and_unrecognized_answers(self):
        answers = {"q23": "", "not_a_real_question": "whatever", "q1": "Engineer"}
        context = _format_questionnaire_context(answers)
        assert "whatever" not in context
        assert "Engineer" in context

    def test_empty_answers_produces_empty_string(self):
        assert _format_questionnaire_context({}) == ""


class TestSystemPrompt:
    def test_still_forbids_diagnosis_and_bdd_reference(self):
        # Regression guard -- these existed before this session's edits and
        # must survive any future prompt tweak.
        assert "never claim a medical diagnosis" in _SYSTEM_PROMPT
        assert "Body Dysmorphic Disorder" in _SYSTEM_PROMPT

    def test_requires_measurement_citation(self):
        assert "cite the actual metric value" in _SYSTEM_PROMPT

    def test_requires_goal_and_motivation_personalization(self):
        assert "stated goal" in _SYSTEM_PROMPT
        assert "motivation for signing up" in _SYSTEM_PROMPT

    def test_requires_extra_care_for_elevated_distress(self):
        assert "elevated distress" in _SYSTEM_PROMPT

    def test_forbids_referencing_medical_answers(self):
        assert "medical conditions" in _SYSTEM_PROMPT
        assert "never for cosmetic commentary" in _SYSTEM_PROMPT
