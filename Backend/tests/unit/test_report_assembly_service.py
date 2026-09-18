from app.services.ai_narrative_service import _FEATURE_SUBSECTIONS
from app.services.facial_assessment_service import ASSESSMENT_CATEGORIES
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.report_assembly_service import (
    assemble_sections,
    classify_recommendations,
    feature_recommendation_tier,
    recommendation_text,
)


_NULL_TAGS = {
    "cost": None,
    "cadence": None,
    "time_to_effect": None,
    "difficulty": None,
    "category": None,
    "risk_level": None,
    "product_or_method": None,
}


def _measurements() -> dict:
    return {feature: {"available": True, "metrics": {"ratio": 1.0}, "note": None} for feature in ANALYSIS_FEATURES}


def _realistic_measurements() -> dict:
    """Uses the actual metric keys facial_assessment_service.py's reference
    tables look up (unlike _measurements()'s placeholder "ratio" key),
    close to their mu reference values -- so feature_scores/facial
    assessments come back available and near the top of their band,
    without needing a real photo fixture in a pure-dict unit test."""
    return {
        "eyebrows": {
            "available": True,
            "metrics": {"left_height_ratio": 0.18, "right_height_ratio": 0.18, "symmetry_delta": 0.0},
            "note": None,
        },
        "eyes": {
            "available": True,
            "metrics": {
                "left_width_ratio": 0.9,
                "right_width_ratio": 0.9,
                "left_openness_ratio": 0.28,
                "right_openness_ratio": 0.28,
                "symmetry_delta": 0.0,
            },
            "note": None,
        },
        "nose": {
            "available": True,
            "metrics": {"width_ratio": 0.7, "length_ratio": 0.7, "width_to_length_ratio": 1.0},
            "note": None,
        },
        "cheeks": {"available": True, "metrics": {"width_to_face_ratio": 0.60}, "note": None},
        "jaw": {"available": True, "metrics": {"width_to_face_ratio": 0.85}, "note": None},
        "lips": {"available": True, "metrics": {"width_ratio": 1.55, "fullness_ratio": 0.1}, "note": None},
        "chin": {"available": True, "metrics": {"projection_to_face_ratio": 0.12}, "note": None},
        "skin": {
            "available": True,
            "metrics": {"mean_r": 200.0, "mean_g": 180.0, "mean_b": 170.0, "tone_variance": 10.0},
            "note": None,
        },
        "ears": {
            "available": True,
            "metrics": {"left_ear_to_nose_ratio": 1.0, "right_ear_to_nose_ratio": 1.0},
            "note": None,
        },
        "hair": {"available": False, "metrics": None, "note": "No dedicated CV geometry."},
        "neck": {"available": False, "metrics": None, "note": "No dedicated CV geometry."},
    }


def _facial_assessments() -> dict:
    return {
        "dimorphism": {
            "available": True,
            "score": 54.0,
            "label": "Moderate",
            "slider_position": 54.0,
            "drivers": [],
            "sub_scores": {},
            "overlay": None,
            "note": None,
        },
        "prototypicality": {
            "available": True,
            "score": 70.0,
            "label": "Above Average",
            "slider_position": 70.0,
            "drivers": None,
            "sub_scores": None,
            "overlay": {"face_outline": []},
            "note": "Typical.",
        },
        "proportions": {
            "available": True,
            "score": 64.0,
            "label": "Fair",
            "slider_position": 64.0,
            "drivers": None,
            "sub_scores": None,
            "overlay": {"upper_ratio": 0.33},
            "note": "Balanced.",
        },
        "symmetry": {
            "available": True,
            "score": 83.0,
            "label": "Quite Symmetric",
            "slider_position": 83.0,
            "drivers": None,
            "sub_scores": {},
            "overlay": {"axis_x": 0.5},
            "note": "Symmetric.",
        },
        "face_shape": {
            "available": True,
            "score": 60.0,
            "label": "Oval",
            "slider_position": 60.0,
            "drivers": None,
            "sub_scores": None,
            "overlay": None,
            "note": "Unconfirmed.",
        },
    }


def _narrative_result() -> dict:
    return {
        "features": {
            feature: {
                "sections": {heading: f"{heading} for {feature}." for heading in _FEATURE_SUBSECTIONS[feature]},
                "summary_callout": feature,
                "strengths": f"Strength for {feature}.",
                "areas_of_note": f"Note for {feature}.",
                "recommendation_ideas": [f"idea about {feature}"],
            }
            for feature in ANALYSIS_FEATURES
        },
        "closing_recommendations": "Use a daily sunscreen. Consider seeing a dermatologist for the jawline.",
    }


class TestAssembleSections:
    def test_contains_all_11_features(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        assert set(sections["features"].keys()) == set(ANALYSIS_FEATURES)

    def test_each_feature_has_sections_callout_and_potential(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        for feature in ANALYSIS_FEATURES:
            entry = sections["features"][feature]
            expected_sections = {heading: f"{heading} for {feature}." for heading in _FEATURE_SUBSECTIONS[feature]}
            assert entry["sections"] == expected_sections
            assert entry["summary_callout"] == feature
            assert entry["strengths"] == f"Strength for {feature}."
            assert entry["areas_of_note"] == f"Note for {feature}."
            assert entry["projected_potential"] == [{"text": f"idea about {feature}", **_NULL_TAGS}]
            assert entry["measurement"]["available"] is True

    def test_attributes_default_to_empty_dict_when_absent(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        for feature in ANALYSIS_FEATURES:
            assert sections["features"][feature]["attributes"] == {}

    def test_attributes_pass_through_when_present(self):
        narrative = _narrative_result()
        narrative["features"]["hair"]["attributes"] = {"hairline": "Full", "texture": "Straight"}
        sections = assemble_sections(_measurements(), narrative)
        assert sections["features"]["hair"]["attributes"] == {"hairline": "Full", "texture": "Straight"}
        assert sections["features"]["jaw"]["attributes"] == {}

    def test_missing_strengths_and_areas_of_note_default_to_empty_string(self):
        narrative = _narrative_result()
        del narrative["features"]["hair"]["strengths"]
        del narrative["features"]["hair"]["areas_of_note"]
        sections = assemble_sections(_measurements(), narrative)
        assert sections["features"]["hair"]["strengths"] == ""
        assert sections["features"]["hair"]["areas_of_note"] == ""

    def test_report_level_sections_present(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        assert sections["intro"]
        assert sections["understanding_your_results"]
        assert sections["limitations"]
        expected = "Use a daily sunscreen. Consider seeing a dermatologist for the jawline."
        assert sections["closing_recommendations"] == expected

    def test_missing_measurement_falls_back_to_unavailable(self):
        measurements = _measurements()
        del measurements["hair"]
        sections = assemble_sections(measurements, _narrative_result())
        assert sections["features"]["hair"]["measurement"]["available"] is False

    def test_recommendations_split_into_three_tiers(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        assert set(sections["recommendations"].keys()) == {"at_home", "otc_skincare", "in_clinic"}


class TestTeaserFallback:
    """narrative_result can still be {} even post-payment -- the DeepSeek
    call can fail after a user has already paid (see
    D:\\zzz\\payment\\plans.md's open items) -- so every feature must still
    have something non-blank to show rather than a blank report."""

    def test_no_narrative_yields_templated_summary_callouts(self):
        sections = assemble_sections(_measurements(), {})
        for feature in ANALYSIS_FEATURES:
            entry = sections["features"][feature]
            assert entry["sections"] == {}
            assert entry["summary_callout"] == "Measurement captured."

    def test_unavailable_measurement_gets_a_different_templated_callout(self):
        measurements = _measurements()
        measurements["hair"] = {"available": False, "metrics": None, "note": "No CV geometry."}
        sections = assemble_sections(measurements, {})
        assert sections["features"]["hair"]["summary_callout"] == "Assessed visually (no direct measurement)."

    def test_real_narrative_takes_over_once_available(self):
        """Same field, same shape -- once narrative exists, the AI text
        wins over the template with no API change."""
        sections = assemble_sections(_measurements(), _narrative_result())
        assert sections["features"]["hair"]["summary_callout"] == "hair"


class TestClassifyRecommendations:
    def test_otc_keyword_classified_as_otc(self):
        features = {"skin": {"recommendation_ideas": ["Try a vitamin C serum daily."]}}
        tiers = classify_recommendations(features)
        assert [item["text"] for item in tiers["otc_skincare"]] == ["Try a vitamin C serum daily."]

    def test_clinic_keyword_classified_as_in_clinic(self):
        features = {"jaw": {"recommendation_ideas": ["Consider seeing a dermatologist about jawline contouring."]}}
        tiers = classify_recommendations(features)
        assert [item["text"] for item in tiers["in_clinic"]] == ["Consider seeing a dermatologist about jawline contouring."]

    def test_generic_advice_defaults_to_at_home(self):
        features = {"skin": {"recommendation_ideas": ["Stay hydrated and get enough sleep."]}}
        tiers = classify_recommendations(features)
        assert [item["text"] for item in tiers["at_home"]] == ["Stay hydrated and get enough sleep."]

    def test_only_recommendation_ideas_are_classified_not_narrative_prose(self):
        """2026-09-17 regression test: Treatment Protocol phases were
        getting padded with long sentence fragments split out of the
        closing-recommendations narrative synthesis (descriptive prose,
        not discrete suggestions) -- only each feature's own
        recommendation_ideas should ever appear in a tier."""
        features = {"skin": {"recommendation_ideas": ["Use a daily sunscreen."]}}
        tiers = classify_recommendations(features)
        assert [item["text"] for item in tiers["otc_skincare"]] == ["Use a daily sunscreen."]
        assert tiers["in_clinic"] == []
        assert tiers["at_home"] == []

    def test_legacy_string_shaped_ideas_still_classify_correctly(self):
        """FR-025 backward compatibility -- a pre-Milestone-3 persisted
        FacialAnalysisResult.narrative_result row has recommendation_ideas
        as bare strings forever (no backfill migration)."""
        features = {"skin": {"recommendation_ideas": ["Try a vitamin C serum daily."]}}
        tiers = classify_recommendations(features)
        assert tiers["otc_skincare"][0] == {"text": "Try a vitamin C serum daily.", **_NULL_TAGS}

    def test_fr025_structured_items_carry_their_metadata_into_the_tier(self):
        features = {
            "skin": {
                "recommendation_ideas": [
                    {
                        "text": "Try a vitamin C serum daily.",
                        "cost": "$20-30",
                        "cadence": "Daily",
                        "difficulty": "Easy",
                        "category": "Cosmetic",
                        "risk_level": "Low",
                        "product_or_method": "Vitamin C Serum",
                    }
                ]
            }
        }
        tiers = classify_recommendations(features)
        assert tiers["otc_skincare"][0] == {
            "text": "Try a vitamin C serum daily.",
            "cost": "$20-30",
            "cadence": "Daily",
            "time_to_effect": None,
            "difficulty": "Easy",
            "category": "Cosmetic",
            "risk_level": "Low",
            "product_or_method": "Vitamin C Serum",
        }

    def test_invalid_difficulty_normalizes_to_none(self):
        features = {"skin": {"recommendation_ideas": [{"text": "Try a vitamin C serum daily.", "difficulty": "Extreme"}]}}
        tiers = classify_recommendations(features)
        assert tiers["otc_skincare"][0]["difficulty"] is None

    def test_item_with_no_usable_text_is_dropped(self):
        features = {"skin": {"recommendation_ideas": [{"cost": "$10"}, "Try a vitamin C serum daily."]}}
        tiers = classify_recommendations(features)
        assert len(tiers["otc_skincare"]) == 1


class TestFeatureRecommendationTier:
    def test_no_ideas_returns_none(self):
        assert feature_recommendation_tier([]) is None

    def test_single_at_home_idea(self):
        assert feature_recommendation_tier(["Stay hydrated and get enough sleep."]) == "at_home"

    def test_single_otc_idea(self):
        assert feature_recommendation_tier(["Try a vitamin C serum daily."]) == "otc_skincare"

    def test_single_in_clinic_idea(self):
        assert (
            feature_recommendation_tier(["Consider seeing a dermatologist about jawline contouring."]) == "in_clinic"
        )

    def test_mixed_ideas_take_the_highest_precedence_tier(self):
        # in_clinic > otc_skincare > at_home, matching _classify_one's own precedence.
        ideas = ["Stay hydrated and get enough sleep.", "Consider seeing a dermatologist about jawline contouring."]
        assert feature_recommendation_tier(ideas) == "in_clinic"

    def test_at_home_and_otc_mixed_prefers_otc(self):
        ideas = ["Stay hydrated and get enough sleep.", "Try a vitamin C serum daily."]
        assert feature_recommendation_tier(ideas) == "otc_skincare"

    def test_still_accepts_fr025_structured_items(self):
        ideas = [{"text": "Try a vitamin C serum daily.", "cost": "$20-30"}]
        assert feature_recommendation_tier(ideas) == "otc_skincare"


class TestRecommendationText:
    def test_extracts_text_from_legacy_bare_string(self):
        assert recommendation_text("Stay hydrated.") == "Stay hydrated."

    def test_extracts_text_from_fr025_structured_item(self):
        assert recommendation_text({"text": "Stay hydrated.", "cost": None}) == "Stay hydrated."

    def test_missing_text_key_returns_empty_string(self):
        assert recommendation_text({"cost": "$10"}) == ""

    def test_non_string_non_dict_returns_empty_string(self):
        assert recommendation_text(None) == ""


class TestNormalizeRecommendationItem:
    def _normalize(self, idea):
        # Exercised indirectly through classify_recommendations elsewhere;
        # here we go through assemble_sections' projected_potential field,
        # the other real caller of the private normalizer.
        sections = assemble_sections(_measurements(), {"features": {"skin": {"recommendation_ideas": [idea]}}})
        return sections["features"]["skin"]["projected_potential"][0]

    def test_legacy_string_item_is_normalized_with_null_metadata(self):
        assert self._normalize("Use a daily moisturizer.") == {"text": "Use a daily moisturizer.", **_NULL_TAGS}

    def test_new_dict_item_passes_through_confirmed_fields(self):
        idea = {
            "text": "Use a daily moisturizer.",
            "cost": "$15-25",
            "cadence": "Nightly",
            "difficulty": "Easy",
            "category": "Cosmetic",
            "risk_level": "Low",
            "product_or_method": "Daily Moisturizer",
        }
        assert self._normalize(idea) == {
            "text": "Use a daily moisturizer.",
            "cost": "$15-25",
            "cadence": "Nightly",
            "time_to_effect": None,
            "difficulty": "Easy",
            "category": "Cosmetic",
            "risk_level": "Low",
            "product_or_method": "Daily Moisturizer",
        }

    def test_invalid_difficulty_normalizes_to_none(self):
        idea = {"text": "Use a daily moisturizer.", "difficulty": "Extreme"}
        assert self._normalize(idea)["difficulty"] is None

    def test_invalid_category_normalizes_to_none(self):
        idea = {"text": "Use a daily moisturizer.", "category": "Surgical"}
        assert self._normalize(idea)["category"] is None

    def test_invalid_risk_level_normalizes_to_none(self):
        idea = {"text": "Use a daily moisturizer.", "risk_level": "Extreme"}
        assert self._normalize(idea)["risk_level"] is None

    def test_empty_text_item_is_dropped(self):
        sections = assemble_sections(
            _measurements(), {"features": {"skin": {"recommendation_ideas": [{"cost": "$10"}]}}}
        )
        assert sections["features"]["skin"]["projected_potential"] == []


class TestFacialAssessmentsBackwardCompatibility:
    """Milestone 2 (FR-018): the 3rd argument is optional specifically so
    every pre-existing call site/test keeps working unmodified."""

    def test_omitted_third_argument_still_returns_all_five_categories_unavailable(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        assert set(sections["facial_assessments"].keys()) == set(ASSESSMENT_CATEGORIES)
        assert all(not entry["available"] for entry in sections["facial_assessments"].values())

    def test_none_third_argument_behaves_the_same_as_omitted(self):
        with_none = assemble_sections(_measurements(), _narrative_result(), None)
        omitted = assemble_sections(_measurements(), _narrative_result())
        assert with_none["facial_assessments"] == omitted["facial_assessments"]

    def test_empty_dict_third_argument_also_falls_back_to_unavailable(self):
        sections = assemble_sections(_measurements(), _narrative_result(), {})
        assert all(not entry["available"] for entry in sections["facial_assessments"].values())

    def test_feature_scores_overall_score_and_harmony_chart_always_present(self):
        """These are derived from `measurements` alone -- present
        regardless of whether facial_assessments was supplied."""
        sections = assemble_sections(_measurements(), _narrative_result())
        assert set(sections["feature_scores"].keys()) == set(ANALYSIS_FEATURES)
        assert "overall_score" in sections
        assert set(sections["harmony_chart"].keys()) == {
            "harmony",
            "symmetry",
            "smoothness",
            "jawline",
            "skin",
            "volume",
        }


class TestFacialAssessmentsPassthrough:
    def test_supplied_assessments_pass_through_unchanged(self):
        assessments = _facial_assessments()
        sections = assemble_sections(_measurements(), _narrative_result(), assessments)
        assert sections["facial_assessments"] == assessments

    def test_partial_assessments_still_yields_all_five_keys(self):
        partial = {"dimorphism": _facial_assessments()["dimorphism"]}
        sections = assemble_sections(_measurements(), _narrative_result(), partial)
        assert set(sections["facial_assessments"].keys()) == set(ASSESSMENT_CATEGORIES)
        assert sections["facial_assessments"]["dimorphism"]["available"] is True
        assert sections["facial_assessments"]["prototypicality"]["available"] is False

    def test_harmony_chart_uses_supplied_assessment_scores(self):
        assessments = _facial_assessments()
        sections = assemble_sections(_realistic_measurements(), _narrative_result(), assessments)
        chart = sections["harmony_chart"]
        expected_harmony = round((70.0 + 64.0 + 83.0) / 3, 1)  # prototypicality + proportions + symmetry
        assert chart["harmony"] == expected_harmony
        assert chart["symmetry"] == 83.0


class TestFeatureScoresWithRealisticMeasurements:
    def test_mesh_features_and_skin_and_ears_score_available(self):
        sections = assemble_sections(_realistic_measurements(), _narrative_result())
        scores = sections["feature_scores"]
        for feature in ("eyebrows", "eyes", "nose", "cheeks", "jaw", "lips", "chin", "skin", "ears"):
            assert scores[feature]["available"] is True, feature
            assert 0.0 <= scores[feature]["score"] <= 100.0, feature

    def test_hair_and_neck_stay_unavailable(self):
        sections = assemble_sections(_realistic_measurements(), _narrative_result())
        scores = sections["feature_scores"]
        assert scores["hair"]["available"] is False
        assert scores["neck"]["available"] is False

    def test_overall_score_is_a_reasonable_composite(self):
        sections = assemble_sections(_realistic_measurements(), _narrative_result())
        assert sections["overall_score"] is not None
        assert 0.0 <= sections["overall_score"] <= 100.0

    def test_no_measurements_yields_none_overall_score(self):
        sections = assemble_sections({}, _narrative_result())
        assert sections["overall_score"] is None
