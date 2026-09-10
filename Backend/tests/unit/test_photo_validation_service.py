from pathlib import Path

from app.services.face_identity_service import (
    IDENTITY_COSINE_DISTANCE_THRESHOLD,
    check_photo_set_identity,
    compute_face_embedding,
    determine_mismatched_angles,
)
from app.services.photo_validation_service import IDENTITY_MISMATCH_THRESHOLD

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


class TestComputeFaceEmbedding:
    def test_real_face_produces_an_embedding(self):
        embedding = compute_face_embedding(_load("pass_all.jpg"))
        assert embedding is not None
        assert embedding.shape == (512,)
        assert abs(float((embedding**2).sum()) - 1.0) < 1e-5

    def test_no_face_returns_none(self):
        assert compute_face_embedding(_load("no_face.jpg")) is None

    def test_unreadable_bytes_returns_none(self):
        assert compute_face_embedding(b"not an image") is None


class TestCheckPhotoSetIdentity:
    def test_same_person_across_all_three_angles_is_consistent(self):
        photos = {
            "front": _load("pass_all.jpg"),
            "right_3q": _load("pass_right_3q.jpg"),
            "left_3q": _load("pass_left_3q.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result == {"consistent": True, "mismatched_angles": [], "message": None}

    def test_different_person_for_one_angle_is_caught_and_named(self):
        photos = {
            "front": _load("pass_all.jpg"),
            "right_3q": _load("different_person.jpg"),
            "left_3q": _load("pass_left_3q.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result["consistent"] is False
        assert result["mismatched_angles"] == ["right_3q"]
        assert result["message"] is not None
        assert "right" in result["message"].lower()

    def test_different_person_for_front_is_caught_and_named(self):
        """Right+left same person, front different → only front is flagged
        (no static 'front is always correct' bias)."""
        photos = {
            "front": _load("different_person.jpg"),
            "right_3q": _load("pass_right_3q.jpg"),
            "left_3q": _load("pass_left_3q.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result["consistent"] is False
        assert result["mismatched_angles"] == ["front"]

    def test_different_person_for_left_3q_is_caught_and_named(self):
        photos = {
            "front": _load("pass_all.jpg"),
            "right_3q": _load("pass_right_3q.jpg"),
            "left_3q": _load("different_person.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result["consistent"] is False
        assert result["mismatched_angles"] == ["left_3q"]

    def test_two_matching_sides_with_different_front_flags_only_front(self):
        """different_person_* fixtures are the same identity (B); pass_all is A.
        So A-front + B-right + B-left correctly flags only front — not a
        static front preference, a genuine vote (sides match each other)."""
        photos = {
            "front": _load("pass_all.jpg"),
            "right_3q": _load("different_person_right_3q.jpg"),
            "left_3q": _load("different_person_left_3q.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result["consistent"] is False
        assert result["mismatched_angles"] == ["front"]

    def test_after_aligning_front_with_left_only_right_remains_flagged(self):
        """User scenario: A/B/C then change front→C → only B (right) flagged."""
        photos = {
            "front": _load("different_person_left_3q.jpg"),  # same person as left
            "right_3q": _load("pass_right_3q.jpg"),  # different person
            "left_3q": _load("different_person_left_3q.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result["consistent"] is False
        assert result["mismatched_angles"] == ["right_3q"]

    def test_fewer_than_three_computable_embeddings_is_trivially_consistent(self):
        photos = {"front": _load("pass_all.jpg"), "right_3q": _load("different_person.jpg")}
        result = check_photo_set_identity(photos)
        assert result == {"consistent": True, "mismatched_angles": [], "message": None}

    def test_a_photo_with_no_detectable_face_is_excluded_not_treated_as_a_mismatch(self):
        photos = {
            "front": _load("pass_all.jpg"),
            "right_3q": _load("pass_right_3q.jpg"),
            "left_3q": _load("no_face.jpg"),
        }
        result = check_photo_set_identity(photos)
        assert result == {"consistent": True, "mismatched_angles": [], "message": None}

    def test_threshold_is_a_real_positive_number(self):
        assert IDENTITY_MISMATCH_THRESHOLD > 0
        assert IDENTITY_COSINE_DISTANCE_THRESHOLD > 0


class TestDetermineMismatchedAngles:
    T = IDENTITY_COSINE_DISTANCE_THRESHOLD

    def test_unique_minimum_match_count_is_the_only_mismatch(self):
        pairwise = {
            ("front", "right_3q"): self.T + 0.2,
            ("front", "left_3q"): self.T - 0.2,
            ("right_3q", "left_3q"): self.T + 0.3,
        }
        assert determine_mismatched_angles(["front", "right_3q", "left_3q"], pairwise) == ["right_3q"]

    def test_front_can_be_the_only_mismatch(self):
        pairwise = {
            ("front", "right_3q"): self.T + 0.2,
            ("front", "left_3q"): self.T + 0.3,
            ("right_3q", "left_3q"): self.T - 0.2,
        }
        assert determine_mismatched_angles(["front", "right_3q", "left_3q"], pairwise) == ["front"]

    def test_all_three_mutually_different_flags_all_angles(self):
        pairwise = {
            ("front", "right_3q"): self.T + 0.5,
            ("front", "left_3q"): self.T + 0.1,
            ("right_3q", "left_3q"): self.T + 0.4,
        }
        result = determine_mismatched_angles(["front", "right_3q", "left_3q"], pairwise)
        assert set(result) == {"front", "right_3q", "left_3q"}

    def test_hub_tie_names_a_single_leaf_without_front_bias(self):
        pairwise = {
            ("front", "right_3q"): self.T - 0.1,
            ("front", "left_3q"): self.T - 0.05,
            ("right_3q", "left_3q"): self.T + 0.2,
        }
        result = determine_mismatched_angles(["front", "right_3q", "left_3q"], pairwise)
        assert len(result) == 1
        assert result[0] in {"right_3q", "left_3q"}
