"""Unit tests for app/services/ai_visual_service.py's pure helper functions
(prompt construction, row-building) -- no DB/AI dependency. Full
lazy-get-or-create/trigger-once/anti-enumeration behavior is covered by
tests/integration/test_ai_visuals_flow.py."""

import uuid

from app.models.ai_visual import AiVisual
from app.services.ai_visual_service import (
    _AGING_STEPS,
    _build_aging_rows,
    _build_prompt,
    _build_variation_rows,
)


class TestBuildAgingRows:
    def test_builds_exactly_three_rows(self):
        rows = _build_aging_rows(uuid.uuid4())
        assert len(rows) == 3

    def test_rows_match_the_confirmed_cadence(self):
        rows = _build_aging_rows(uuid.uuid4())
        ages = [row.attributes["age_years"] for row in rows]
        assert ages == [31, 33, 38]

    def test_rows_are_never_marked_recommended(self):
        rows = _build_aging_rows(uuid.uuid4())
        assert all(row.is_recommended is False for row in rows)

    def test_variation_index_matches_step_order(self):
        rows = _build_aging_rows(uuid.uuid4())
        assert [row.variation_index for row in rows] == [0, 1, 2]


class TestBuildVariationRows:
    def test_builds_exactly_five_rows(self):
        rows = _build_variation_rows(uuid.uuid4(), "hairstyle", "Oval", None)
        assert len(rows) == 5

    def test_first_row_is_recommended_and_only_the_first(self):
        rows = _build_variation_rows(uuid.uuid4(), "hairstyle", "Round", None)
        assert rows[0].is_recommended is True
        assert all(not row.is_recommended for row in rows[1:])

    def test_every_row_has_a_name_and_explanation(self):
        rows = _build_variation_rows(uuid.uuid4(), "outfit", None, "Masculine")
        for row in rows:
            assert row.name
            assert row.explanation


class TestBuildPrompt:
    def test_aging_prompt_cites_the_target_age(self):
        row = AiVisual(kind="aging", variation_index=0, name="Near term", attributes={"age_years": 31})
        prompt = _build_prompt("aging", row)
        assert "31" in prompt
        assert "identity" in prompt.lower()

    def test_hairstyle_prompt_cites_the_variation_name(self):
        row = AiVisual(kind="hairstyle", variation_index=0, name="Soft Layered Bob", explanation="A soft cut.")
        prompt = _build_prompt("hairstyle", row)
        assert "Soft Layered Bob" in prompt
        assert "A soft cut." in prompt

    def test_outfit_prompt_mentions_shoulder_up_framing(self):
        row = AiVisual(kind="outfit", variation_index=0, name="Minimalist Monochrome", explanation="Clean lines.")
        prompt = _build_prompt("outfit", row)
        assert "shoulder" in prompt.lower()
        assert "Minimalist Monochrome" in prompt


def test_aging_steps_constant_matches_confirmed_cadence():
    assert _AGING_STEPS == ((31, "Near term"), (33, "Mid range"), (38, "Longer range"))
