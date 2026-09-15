from app.services.facial_assessment_service import ASSESSMENT_CATEGORIES
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.report_assembly_service import (
    assemble_sections,
    classify_recommendations,
    feature_recommendation_tier,
)


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
                "narrative": f"Narrative for {feature}.",
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

    def test_each_feature_has_narrative_callout_and_potential(self):
        sections = assemble_sections(_measurements(), _narrative_result())
        for feature in ANALYSIS_FEATURES:
            entry = sections["features"][feature]
            assert entry["narrative"] == f"Narrative for {feature}."
            assert entry["summary_callout"] == feature
            assert entry["strengths"] == f"Strength for {feature}."
            assert entry["areas_of_note"] == f"Note for {feature}."
            assert entry["projected_potential"] == [f"idea about {feature}"]
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
            assert entry["narrative"] == ""
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
        tiers = classify_recommendations(features, "")
        assert "Try a vitamin C serum daily." in tiers["otc_skincare"]

    def test_clinic_keyword_classified_as_in_clinic(self):
        features = {"jaw": {"recommendation_ideas": ["Consider seeing a dermatologist about jawline contouring."]}}
        tiers = classify_recommendations(features, "")
        assert "Consider seeing a dermatologist about jawline contouring." in tiers["in_clinic"]

    def test_generic_advice_defaults_to_at_home(self):
        features = {"skin": {"recommendation_ideas": ["Stay hydrated and get enough sleep."]}}
        tiers = classify_recommendations(features, "")
        assert "Stay hydrated and get enough sleep." in tiers["at_home"]

    def test_closing_recommendations_text_is_also_classified(self):
        tiers = classify_recommendations({}, "Use a daily sunscreen. Consider seeing a dermatologist for the jawline.")
        assert any("sunscreen" in item for item in tiers["otc_skincare"])
        assert any("dermatologist" in item for item in tiers["in_clinic"])


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
