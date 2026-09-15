import json

from app.services.ai_narrative_service import (
    _FEATURE_ATTRIBUTE_KEYS,
    _SYSTEM_PROMPT,
    _parse_facial_age,
    _parse_hair_loss,
    _parse_response,
    _sanitize_attributes,
    format_questionnaire_context,
)
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.questionnaire_service import QUESTIONS_BY_ID
from app.exceptions import AIProviderError


class TestFormatQuestionnaireContext:
    def test_pairs_each_answer_with_its_real_question_text(self):
        answers = {"q4": "Masculine", "q14": "My eyes", "q18": "Undecided"}
        context = format_questionnaire_context(answers)

        assert f"{QUESTIONS_BY_ID['q4'].text}: Masculine" in context
        assert f"{QUESTIONS_BY_ID['q14'].text}: My eyes" in context
        assert f"{QUESTIONS_BY_ID['q18'].text}: Undecided" in context

    def test_never_emits_raw_opaque_question_ids(self):
        # The whole point of this function is that the AI never sees a bare
        # "q15" -- only the real question text -- so a raw key must never
        # appear as its own line.
        answers = {"q15": "My nose"}
        context = format_questionnaire_context(answers)
        assert "q15:" not in context
        assert "My nose" in context

    def test_skips_blank_and_unrecognized_answers(self):
        answers = {"q23": "", "not_a_real_question": "whatever", "q1": "Engineer"}
        context = format_questionnaire_context(answers)
        assert "whatever" not in context
        assert "Engineer" in context

    def test_empty_answers_produces_empty_string(self):
        assert format_questionnaire_context({}) == ""


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

    def test_requires_facial_age_and_hair_loss_estimates(self):
        assert '"facial_age"' in _SYSTEM_PROMPT
        assert '"hair_loss"' in _SYSTEM_PROMPT
        assert "use JSON null" in _SYSTEM_PROMPT

    def test_requires_four_paragraph_closing_recommendations(self):
        assert "exactly 4 short paragraphs" in _SYSTEM_PROMPT
        assert "periorbital/eye region" in _SYSTEM_PROMPT

    def test_includes_every_feature_attribute_vocabulary(self):
        for feature, keys in _FEATURE_ATTRIBUTE_KEYS.items():
            assert feature in _SYSTEM_PROMPT
            for key in keys:
                assert key in _SYSTEM_PROMPT, f"{feature}.{key}"

    def test_forbids_fabricating_attribute_keys(self):
        assert "never guess a value just to fill every key" in _SYSTEM_PROMPT
        assert "never a key not in that feature's own vocabulary list" in _SYSTEM_PROMPT


class TestSanitizeAttributes:
    def test_keeps_only_allowed_keys_with_string_values(self):
        raw = {"hairline": "Full", "texture": "Straight", "not_a_real_key": "x", "density": 5}
        assert _sanitize_attributes("hair", raw) == {"hairline": "Full", "texture": "Straight"}

    def test_non_dict_input_returns_empty(self):
        assert _sanitize_attributes("hair", None) == {}
        assert _sanitize_attributes("hair", "Full hairline") == {}

    def test_empty_string_value_is_dropped(self):
        assert _sanitize_attributes("hair", {"hairline": ""}) == {}

    def test_unknown_feature_yields_no_allowed_keys(self):
        assert _sanitize_attributes("not_a_feature", {"hairline": "Full"}) == {}


def _minimal_features() -> dict:
    return {
        feature: {
            "narrative": "n",
            "summary_callout": "s",
            "strengths": "st",
            "areas_of_note": "a",
            "recommendation_ideas": [],
        }
        for feature in ANALYSIS_FEATURES
    }


class TestParseFacialAge:
    def test_valid_estimate_is_kept(self):
        assert _parse_facial_age({"estimate": 28, "note": "context"}) == {"estimate": 28, "note": "context"}

    def test_missing_note_defaults_to_none(self):
        assert _parse_facial_age({"estimate": 30}) == {"estimate": 30, "note": None}

    def test_null_is_passed_through_as_none(self):
        assert _parse_facial_age(None) is None

    def test_out_of_range_estimate_is_rejected(self):
        assert _parse_facial_age({"estimate": 200}) is None
        assert _parse_facial_age({"estimate": 0}) is None

    def test_non_int_estimate_is_rejected(self):
        assert _parse_facial_age({"estimate": "28"}) is None
        assert _parse_facial_age({"estimate": 28.5}) is None

    def test_bool_estimate_is_rejected(self):
        # bool is a subclass of int in Python -- must not slip through.
        assert _parse_facial_age({"estimate": True}) is None


class TestParseHairLoss:
    def test_valid_stage_is_kept(self):
        assert _parse_hair_loss({"stage": 3, "label": "Early thinning"}) == {"stage": 3, "label": "Early thinning"}

    def test_null_is_passed_through_as_none(self):
        assert _parse_hair_loss(None) is None

    def test_stage_out_of_1_to_7_range_is_rejected(self):
        assert _parse_hair_loss({"stage": 0, "label": "x"}) is None
        assert _parse_hair_loss({"stage": 8, "label": "x"}) is None

    def test_missing_or_empty_label_is_rejected(self):
        assert _parse_hair_loss({"stage": 2}) is None
        assert _parse_hair_loss({"stage": 2, "label": ""}) is None


class TestParseResponse:
    def test_facial_age_and_hair_loss_default_to_none_when_absent(self):
        raw = json.dumps({"features": _minimal_features(), "closing_recommendations": "c"})
        result = _parse_response(raw)
        assert result.facial_age is None
        assert result.hair_loss is None

    def test_attributes_are_sanitized_per_feature_in_the_full_response(self):
        features = _minimal_features()
        features["hair"]["attributes"] = {"hairline": "Full", "made_up_key": "x", "texture": ""}
        features["jaw"]["attributes"] = {"hairline": "Full", "mandibular_definition": "Angular"}
        raw = json.dumps({"features": features, "closing_recommendations": "c"})
        result = _parse_response(raw)
        assert result.features["hair"]["attributes"] == {"hairline": "Full"}
        # "hairline" isn't in jaw's own vocabulary -- must be dropped.
        assert result.features["jaw"]["attributes"] == {"mandibular_definition": "Angular"}

    def test_missing_attributes_key_becomes_empty_dict(self):
        raw = json.dumps({"features": _minimal_features(), "closing_recommendations": "c"})
        result = _parse_response(raw)
        for feature in ANALYSIS_FEATURES:
            assert result.features[feature]["attributes"] == {}

    def test_facial_age_and_hair_loss_are_parsed_when_present(self):
        raw = json.dumps(
            {
                "features": _minimal_features(),
                "closing_recommendations": "c",
                "facial_age": {"estimate": 25, "note": "n"},
                "hair_loss": {"stage": 1, "label": "Normal"},
            }
        )
        result = _parse_response(raw)
        assert result.facial_age == {"estimate": 25, "note": "n"}
        assert result.hair_loss == {"stage": 1, "label": "Normal"}

    def test_malformed_facial_age_does_not_fail_the_whole_response(self):
        raw = json.dumps(
            {"features": _minimal_features(), "closing_recommendations": "c", "facial_age": {"estimate": "not a number"}}
        )
        result = _parse_response(raw)
        assert result.facial_age is None
        assert result.closing_recommendations == "c"

    def test_still_raises_when_features_key_is_missing(self):
        raw = json.dumps({"closing_recommendations": "c"})
        try:
            _parse_response(raw)
            assert False, "expected AIProviderError"
        except AIProviderError:
            pass
