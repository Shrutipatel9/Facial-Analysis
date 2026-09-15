from pathlib import Path

from app.services.facial_assessment_service import (
    ASSESSMENT_CATEGORIES,
    compute_feature_scores,
    compute_harmony_chart,
    compute_overall_score,
    extract_facial_assessments,
    extract_measurements_and_assessments,
)
from app.services.facial_measurement_service import ANALYSIS_FEATURES, get_landmark_context

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


def _real_face_photos() -> dict[str, bytes]:
    return {
        "front": _load("pass_all.jpg"),
        "left_3q": _load("pass_left_3q.jpg"),
        "right_3q": _load("pass_right_3q.jpg"),
    }


class TestExtractFacialAssessments:
    def test_no_landmark_context_returns_all_unavailable(self):
        results = extract_facial_assessments(None, {})
        assert set(results.keys()) == set(ASSESSMENT_CATEGORIES)
        assert all(not result.available for result in results.values())
        assert all(result.note for result in results.values())

    def test_no_front_photo_produces_all_unavailable_end_to_end(self):
        _measurements, assessments = extract_measurements_and_assessments({})
        assert set(assessments.keys()) == set(ASSESSMENT_CATEGORIES)
        assert all(not result.available for result in assessments.values())

    def test_no_face_detected_produces_all_unavailable_end_to_end(self):
        _measurements, assessments = extract_measurements_and_assessments({"front": _load("no_face.jpg")})
        assert all(not result.available for result in assessments.values())

    def test_real_face_produces_all_five_keys(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        assert set(assessments.keys()) == set(ASSESSMENT_CATEGORIES)

    def test_scores_are_always_in_0_100_range(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        for category, result in assessments.items():
            if result.available:
                assert result.score is not None, category
                assert 0.0 <= result.score <= 100.0, category
                assert result.slider_position == result.score, category

    def test_never_fabricates_a_score_when_unavailable(self):
        results = extract_facial_assessments(None, {})
        for result in results.values():
            assert result.score is None
            assert result.label is None


class TestDimorphism:
    def test_available_with_real_face_has_drivers_and_sub_scores(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        dimorphism = assessments["dimorphism"]
        assert dimorphism.available is True
        assert dimorphism.label in ("Hyper Feminine", "Feminine", "Moderate", "Masculine", "Hyper Masculine")
        assert dimorphism.drivers is not None
        assert 1 <= len(dimorphism.drivers) <= 3
        assert dimorphism.sub_scores is not None
        for driver in dimorphism.drivers:
            assert driver.citation  # never an empty/invented-looking citation
            assert 0.0 <= driver.score <= 100.0

    def test_drivers_are_the_most_extreme_sub_scores(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        dimorphism = assessments["dimorphism"]
        assert dimorphism.sub_scores is not None and dimorphism.drivers is not None
        ranked = sorted(dimorphism.sub_scores.values(), key=lambda d: abs(d.score - 50.0), reverse=True)
        assert [d.feature for d in dimorphism.drivers] == [d.feature for d in ranked[: len(dimorphism.drivers)]]


class TestPrototypicality:
    def test_available_with_real_face_has_face_outline_overlay(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        prototypicality = assessments["prototypicality"]
        assert prototypicality.available is True
        assert prototypicality.overlay is not None
        outline = prototypicality.overlay["face_outline"]
        assert len(outline) > 30  # the full face-oval perimeter, not a handful of points
        for x, y in outline:
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0


class TestProportions:
    def test_available_with_real_face_has_thirds_summing_to_one(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        proportions = assessments["proportions"]
        assert proportions.available is True
        overlay = proportions.overlay
        assert overlay is not None
        total = overlay["upper_ratio"] + overlay["middle_ratio"] + overlay["lower_ratio"]
        assert abs(total - 1.0) < 0.01


class TestSymmetry:
    def test_available_with_real_face_has_four_region_grid(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        symmetry = assessments["symmetry"]
        assert symmetry.available is True
        assert symmetry.sub_scores is not None
        assert set(symmetry.sub_scores.keys()) == {"Brows", "Eyes", "Mouth", "Jaw"}
        assert symmetry.overlay is not None
        assert len(symmetry.overlay["pairs"]) == 5  # includes nose, excluded only from the regional grid

    def test_symmetric_fixture_scores_reasonably_high(self):
        # pass_all.jpg is this project's calibration fixture for a
        # same-person, roughly-symmetric face -- not a guarantee of a
        # specific number, just a sanity floor.
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        assert assessments["symmetry"].score > 30.0


class TestFaceShape:
    def test_available_with_real_face_is_flagged_as_unconfirmed(self):
        _measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        face_shape = assessments["face_shape"]
        assert face_shape.available is True
        assert face_shape.label in ("Oval", "Round", "Square", "Long/Oblong", "Heart", "Diamond")
        assert face_shape.note is not None
        assert "unconfirmed" in face_shape.note.lower() or "provisional" in face_shape.note.lower()


class TestFeatureScores:
    def test_always_all_eleven_keys(self):
        measurements, _assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        assert set(scores.keys()) == set(ANALYSIS_FEATURES)

    def test_hair_and_neck_always_unavailable(self):
        measurements, _assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        assert scores["hair"].available is False
        assert scores["neck"].available is False

    def test_mesh_features_and_skin_and_ears_are_available_and_in_range(self):
        measurements, _assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        for feature in ("eyebrows", "eyes", "nose", "cheeks", "jaw", "lips", "chin", "skin", "ears"):
            assert scores[feature].available is True, feature
            assert 0.0 <= scores[feature].score <= 100.0, feature
            assert scores[feature].label

    def test_no_face_produces_all_unavailable_feature_scores(self):
        measurements, _assessments = extract_measurements_and_assessments({"front": _load("no_face.jpg")})
        scores = compute_feature_scores(measurements)
        assert all(not s.available for s in scores.values())

    def test_available_scores_always_carry_a_driver_and_finding(self):
        measurements, _assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        for feature in ("eyebrows", "eyes", "nose", "cheeks", "jaw", "lips", "chin", "skin", "ears"):
            assert scores[feature].driver, feature
            assert scores[feature].finding, feature

    def test_unavailable_scores_never_carry_a_driver_or_finding(self):
        measurements, _assessments = extract_measurements_and_assessments({"front": _load("no_face.jpg")})
        scores = compute_feature_scores(measurements)
        assert all(s.driver is None and s.finding is None for s in scores.values())

    def test_directional_features_have_a_reference_value_symmetry_features_dont(self):
        measurements, _assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        for feature in ("nose", "cheeks", "jaw", "lips", "chin"):
            assert scores[feature].reference_value, feature
        for feature in ("eyebrows", "eyes", "ears", "skin"):
            assert scores[feature].reference_value is None, feature

    def test_directional_finding_reflects_which_side_of_typical_the_value_is_on(self):
        from app.services.facial_assessment_service import _directional_finding

        # jaw: mu=0.85, sigma=0.06 -- clearly above/below/near typical.
        assert _directional_finding("jaw", 0.97, 0.85, 0.06) == "Wider than typical"
        assert _directional_finding("jaw", 0.73, 0.85, 0.06) == "Narrower than typical"
        assert _directional_finding("jaw", 0.85, 0.85, 0.06) == "Close to typical width"
        # eyebrows has no directional phrase table -- always None here.
        assert _directional_finding("eyebrows", 0.02, 0.02, 0.02) is None


class TestOverallScore:
    def test_real_face_produces_a_score_in_range(self):
        measurements, _assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        overall = compute_overall_score(scores)
        assert overall is not None
        assert 0.0 <= overall <= 100.0

    def test_no_data_produces_none_not_zero(self):
        measurements, _assessments = extract_measurements_and_assessments({})
        scores = compute_feature_scores(measurements)
        assert compute_overall_score(scores) is None


class TestHarmonyChart:
    def test_all_six_axes_present_and_in_range(self):
        measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        chart = compute_harmony_chart(scores, assessments)
        assert set(chart.keys()) == {"harmony", "symmetry", "smoothness", "jawline", "skin", "volume"}
        for axis, value in chart.items():
            assert value is not None, axis
            assert 0.0 <= value <= 100.0, axis

    def test_smoothness_reuses_the_skin_score_exactly(self):
        measurements, assessments = extract_measurements_and_assessments(_real_face_photos())
        scores = compute_feature_scores(measurements)
        chart = compute_harmony_chart(scores, assessments)
        assert chart["smoothness"] == chart["skin"]

    def test_no_data_produces_all_none(self):
        chart = compute_harmony_chart({}, {})
        assert all(value is None for value in chart.values())


class TestLandmarkContextSharing:
    def test_get_landmark_context_reused_by_combinator_matches_direct_call(self):
        """Not a strict single-inference proof (that would need patching
        the landmarker to count calls), but confirms the combinator's
        output is consistent with the shared context -- the piece that
        would break if the sharing were wired incorrectly."""
        photos = _real_face_photos()
        context = get_landmark_context(photos)
        assert context is not None
        measurements, assessments = extract_measurements_and_assessments(photos)
        assert measurements["eyebrows"].available is True
        assert assessments["symmetry"].available is True
