import pytest

from app.services.password_service import validate_password_strength


class TestPasswordStrength:
    def test_accepts_valid_password(self):
        validate_password_strength("correcthorse9", "user@example.com")  # should not raise

    @pytest.mark.parametrize(
        "password",
        [
            "short1a",  # too short
            "nodigitshere",  # no digit
            "12345678901",  # no letter
        ],
    )
    def test_rejects_weak_passwords(self, password):
        with pytest.raises(ValueError):
            validate_password_strength(password, "user@example.com")

    def test_rejects_password_matching_email_local_part(self):
        with pytest.raises(ValueError):
            validate_password_strength("Jsmith123", "Jsmith123@example.com")

    def test_rejects_over_max_length(self):
        with pytest.raises(ValueError):
            validate_password_strength("a1" * 100, "user@example.com")
