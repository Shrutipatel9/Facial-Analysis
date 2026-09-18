from pathlib import Path
from types import SimpleNamespace

from app.services.facial_measurement_service import (
    ANALYSIS_FEATURES,
    _angle_degrees,
    _tilt_degrees,
    extract_measurements,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


class TestExtractMeasurements:
    def test_no_front_photo_returns_all_unavailable(self):
        results = extract_measurements({})
        assert set(results.keys()) == set(ANALYSIS_FEATURES)
        assert all(not result.available for result in results.values())

    def test_no_face_detected_returns_all_unavailable(self):
        results = extract_measurements({"front": _load("no_face.jpg")})
        assert set(results.keys()) == set(ANALYSIS_FEATURES)
        assert all(not result.available for result in results.values())

    def test_real_face_produces_all_eleven_keys(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        assert set(results.keys()) == set(ANALYSIS_FEATURES)

    def test_hair_and_neck_are_always_unavailable_by_design(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        assert results["hair"].available is False
        assert results["neck"].available is False
        assert results["hair"].note is not None
        assert results["neck"].note is not None

    def test_mesh_friendly_features_produce_real_metrics(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        for feature in ("eyebrows", "eyes", "nose", "cheeks", "jaw", "lips", "chin"):
            result = results[feature]
            assert result.available is True, feature
            assert result.metrics
            assert all(isinstance(v, float) for v in result.metrics.values())

    def test_skin_and_ears_produce_metrics_with_a_limitation_note(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        for feature in ("skin", "ears"):
            result = results[feature]
            assert result.available is True, feature
            assert result.metrics
            assert result.note is not None

    def test_symmetric_face_has_small_symmetry_delta(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        assert results["eyes"].metrics["symmetry_delta"] < 0.05
        assert results["eyebrows"].metrics["symmetry_delta"] < 0.05

    def test_ears_uses_side_angle_photos_when_available(self):
        """Front-facing photos show ears poorly at best (see this
        module's docstring) -- when left_3q/right_3q are supplied, ears
        must be measured from those, not silently fall back to front."""
        front_only = extract_measurements({"front": _load("pass_all.jpg")})["ears"]
        with_angles = extract_measurements(
            {
                "front": _load("pass_all.jpg"),
                "left_3q": _load("pass_left_3q.jpg"),
                "right_3q": _load("pass_right_3q.jpg"),
            }
        )["ears"]

        assert front_only.available is True
        assert with_angles.available is True
        assert set(with_angles.metrics.keys()) == {"left_ear_to_nose_ratio", "right_ear_to_nose_ratio"}
        # The side-angle-derived values are real measurements from a
        # different photo/geometry than the front-only fallback -- they
        # should not just be a copy of whatever front alone would produce.
        assert with_angles.metrics != front_only.metrics

    def test_ears_falls_back_to_front_when_a_side_angle_is_missing(self):
        results = extract_measurements({"front": _load("pass_all.jpg"), "left_3q": _load("pass_left_3q.jpg")})
        ears = results["ears"]
        assert ears.available is True
        assert "left_ear_to_nose_ratio" in ears.metrics
        assert "right_ear_to_nose_ratio" in ears.metrics  # fell back to front


class TestPhase14FeatureScoresBackwardCompatibility:
    """Phase 14 (Milestone 3, FR-023) regression guard -- every metric key
    that existed before this phase (and that facial_assessment_service.py
    reads by name) must still be present with the same meaning, additive
    only."""

    def test_fr018_metric_keys_are_unchanged_and_still_present(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        expected_keys = {
            "eyebrows": {"left_height_ratio", "right_height_ratio", "symmetry_delta"},
            "eyes": {
                "left_width_ratio",
                "right_width_ratio",
                "left_openness_ratio",
                "right_openness_ratio",
                "symmetry_delta",
            },
            "nose": {"width_ratio", "length_ratio", "width_to_length_ratio"},
            "cheeks": {"width_to_face_ratio"},
            "jaw": {"width_to_face_ratio"},
            "lips": {"width_ratio", "fullness_ratio"},
            "chin": {"projection_to_face_ratio"},
        }
        for feature, keys in expected_keys.items():
            assert keys.issubset(results[feature].metrics.keys()), feature


class TestPhase14NewMetrics:
    def test_new_metrics_present_and_are_floats(self):
        results = extract_measurements({"front": _load("pass_all.jpg")})
        new_keys = {
            "eyebrows": {
                "left_tilt_deg",
                "right_tilt_deg",
                "interbrow_distance_ratio",
                "left_length_ratio",
                "right_length_ratio",
            },
            "eyes": {
                "left_canthal_tilt_deg",
                "right_canthal_tilt_deg",
                "left_shape_ratio",
                "right_shape_ratio",
                "intercanthal_to_face_width_ratio",
                "interpupillary_distance_ratio",
            },
            "nose": {"tip_position_ratio", "columella_deviation_ratio"},
            "cheeks": {"cheek_to_jaw_ratio", "cheekbone_height_ratio", "symmetry_delta"},
            "jaw": {
                "jaw_to_cheek_ratio",
                "left_jaw_contour_angle_deg",
                "right_jaw_contour_angle_deg",
                "length_ratio",
                "flare_symmetry_delta",
            },
            "lips": {
                "upper_lip_thickness_ratio",
                "lower_lip_thickness_ratio",
                "upper_to_lower_ratio",
                "oral_commissure_tilt_deg",
            },
            "chin": {"width_ratio", "symmetry_delta"},
        }
        for feature, keys in new_keys.items():
            metrics = results[feature].metrics
            assert keys.issubset(metrics.keys()), feature
            for key in keys:
                assert isinstance(metrics[key], float), f"{feature}.{key}"

    def test_angle_metrics_are_in_plausible_ranges(self):
        """Regression guard for the two bugs caught during this phase's
        planning: a mirrored-sign bug on tilt metrics (would show as a
        value near +-90 instead of a small number) and a degenerate
        near-collinear angle (would show as a value near 0 or 180)."""
        results = extract_measurements({"front": _load("pass_all.jpg")})
        eyebrows, eyes, jaw, lips = (
            results[feature].metrics for feature in ("eyebrows", "eyes", "jaw", "lips")
        )
        for key in ("left_canthal_tilt_deg", "right_canthal_tilt_deg"):
            assert -45 < eyes[key] < 45, key
        for key in ("left_tilt_deg", "right_tilt_deg"):
            assert -45 < eyebrows[key] < 45, key
        assert -45 < lips["oral_commissure_tilt_deg"] < 45
        for key in ("left_jaw_contour_angle_deg", "right_jaw_contour_angle_deg"):
            assert 60 < jaw[key] < 170, key

    def test_interpupillary_distance_is_wider_than_intercanthal_distance(self):
        """Pupils always sit wider apart than the inner eye corners -- if
        this doesn't hold, the iris-center landmark indices are wrong."""
        eyes = extract_measurements({"front": _load("pass_all.jpg")})["eyes"].metrics
        assert eyes["interpupillary_distance_ratio"] > eyes["intercanthal_to_face_width_ratio"]


class TestTiltDegrees:
    @staticmethod
    def _landmarks(points: dict[int, tuple[float, float]]) -> list[SimpleNamespace]:
        size = max(points) + 1
        result = [SimpleNamespace(x=0.0, y=0.0) for _ in range(size)]
        for index, (x, y) in points.items():
            result[index] = SimpleNamespace(x=x, y=y)
        return result

    def test_level_pair_returns_near_zero(self):
        landmarks = self._landmarks({0: (0.1, 0.5), 1: (0.2, 0.5)})
        assert abs(_tilt_degrees(landmarks, 0, 1)) < 0.01

    def test_mirrored_pairs_with_the_same_real_tilt_share_a_sign(self):
        """The exact bug class caught during Phase 14 planning: 'outer'
        sits on the smaller-x side of 'inner' for a left-side pair but the
        larger-x side for a mirrored right-side pair. Both configurations
        below represent the same real-world tilt (far point higher than
        near) and must report the same sign."""
        left_like = self._landmarks({0: (0.3, 0.5), 1: (0.2, 0.4)})  # far (1) is left of near, and higher
        right_like = self._landmarks({0: (0.6, 0.5), 1: (0.7, 0.4)})  # far (1) is right of near, and higher
        left_tilt = _tilt_degrees(left_like, 0, 1)
        right_tilt = _tilt_degrees(right_like, 0, 1)
        assert left_tilt > 0
        assert right_tilt > 0


class TestAngleDegrees:
    @staticmethod
    def _landmarks(points: dict[int, tuple[float, float]]) -> list[SimpleNamespace]:
        size = max(points) + 1
        result = [SimpleNamespace(x=0.0, y=0.0) for _ in range(size)]
        for index, (x, y) in points.items():
            result[index] = SimpleNamespace(x=x, y=y)
        return result

    def test_collinear_points_return_near_180(self):
        landmarks = self._landmarks({0: (0.0, 0.0), 1: (0.5, 0.0), 2: (1.0, 0.0)})
        assert abs(_angle_degrees(landmarks, 0, 1, 2) - 180.0) < 0.01

    def test_right_angle_returns_near_90(self):
        landmarks = self._landmarks({0: (1.0, 0.0), 1: (0.0, 0.0), 2: (0.0, 1.0)})
        assert abs(_angle_degrees(landmarks, 0, 1, 2) - 90.0) < 0.01

    def test_zero_length_vector_returns_zero_not_an_error(self):
        landmarks = self._landmarks({0: (0.0, 0.0), 1: (0.0, 0.0), 2: (1.0, 1.0)})
        assert _angle_degrees(landmarks, 0, 1, 2) == 0.0
