import pytest

from app.services.chat_refusal_keywords import REFUSAL_MESSAGE, is_medical_question


class TestIsMedicalQuestion:
    @pytest.mark.parametrize(
        "text",
        [
            "Can I use minoxidil for my hair loss?",
            "What dosage of retinoid should I use?",
            "Should I take Accutane for my acne?",
            "What prescription would help my skin?",
            "Can you prescribe something for me?",
            "Is there a drug interaction I should worry about?",
            "Please diagnose me with something.",
            "What's the right dosage for this medication?",
            "Are there side effects I should know about?",
            "Is it safe to take isotretinoin?",
        ],
    )
    def test_flags_medical_questions(self, text):
        assert is_medical_question(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "What should I focus on for skin quality?",
            "Which hairstyle direction fits my oval face shape?",
            "What are my top improvement priorities?",
            "Can you diagnose my face shape from these measurements?",
            "Is drug store makeup okay for everyday wear?",
            "How should I track progress over 30 days?",
            "Tell me about my jaw symmetry.",
        ],
    )
    def test_does_not_flag_legitimate_report_questions(self, text):
        assert is_medical_question(text) is False

    def test_case_insensitive(self):
        assert is_medical_question("MINOXIDIL for hair growth") is True

    def test_empty_string_is_not_flagged(self):
        assert is_medical_question("") is False


def test_refusal_message_redirects_to_a_professional():
    assert "professional" in REFUSAL_MESSAGE.lower()
    assert REFUSAL_MESSAGE.strip() != ""
