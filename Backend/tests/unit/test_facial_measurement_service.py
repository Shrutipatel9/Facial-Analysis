from pathlib import Path

from app.services.facial_measurement_service import ANALYSIS_FEATURES, extract_measurements

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
