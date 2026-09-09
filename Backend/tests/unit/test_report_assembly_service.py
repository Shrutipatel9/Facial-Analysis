from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.report_assembly_service import assemble_sections, classify_recommendations


def _measurements() -> dict:
    return {
        feature: {"available": True, "metrics": {"ratio": 1.0}, "note": None} for feature in ANALYSIS_FEATURES
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
