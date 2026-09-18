"""Unit tests for app/services/ai_visual_service.py's pure helper functions
(prompt construction, row-building) -- no DB/AI dependency. Full
lazy-get-or-create/trigger-once/anti-enumeration behavior is covered by
tests/integration/test_ai_visuals_flow.py."""

import uuid
from types import SimpleNamespace

from app.models.ai_visual import AiVisual
from app.services.ai_visual_service import (
    _AGING_STEPS,
    _POTENTIAL_FALLBACK_SUGGESTION,
    _build_aging_rows,
    _build_potential_rows,
    _build_prompt,
    _build_variation_rows,
)

_FAKE_ANALYSIS = SimpleNamespace(measurements={}, narrative_result={}, facial_assessments={})
"""A minimal stand-in for FacialAnalysisResult -- _build_potential_rows
only reads .measurements/.narrative_result/.facial_assessments, all passed
straight through to report_assembly_service.assemble_sections (already
unit-tested on its own terms in test_report_assembly_service.py), so these
tests monkeypatch that boundary instead of hand-crafting real CV
measurements that would score into specific bands -- keeps this test
focused on _build_potential_rows' own ranking/fallback logic, not on
facial_assessment_service's scoring internals."""


def _fake_sections(feature_scores: dict, projected_potential: dict) -> dict:
    return {
        "feature_scores": feature_scores,
        "features": {feature: {"projected_potential": ideas} for feature, ideas in projected_potential.items()},
    }


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


class TestBuildPotentialRows:
    def test_builds_exactly_one_row(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.ai_visual_service.assemble_sections",
            lambda *a, **k: _fake_sections({}, {}),
        )
        rows = _build_potential_rows(uuid.uuid4(), _FAKE_ANALYSIS)
        assert len(rows) == 1
        assert rows[0].kind == "potential"
        assert rows[0].variation_index == 0
        assert rows[0].is_recommended is False

    def test_falls_back_to_the_generic_suggestion_when_nothing_needs_attention(self, monkeypatch):
        feature_scores = {
            "skin": {"available": True, "score": 92.0, "label": "Excellent"},
            "jaw": {"available": True, "score": 85.0, "label": "Good"},
        }
        monkeypatch.setattr(
            "app.services.ai_visual_service.assemble_sections",
            lambda *a, **k: _fake_sections(feature_scores, {}),
        )
        rows = _build_potential_rows(uuid.uuid4(), _FAKE_ANALYSIS)
        assert rows[0].explanation == _POTENTIAL_FALLBACK_SUGGESTION
        assert rows[0].attributes["priority_features"] == []

    def test_uses_the_lowest_scoring_needs_attention_features_first(self, monkeypatch):
        feature_scores = {
            "skin": {"available": True, "score": 30.0, "label": "Needs Attention"},
            "jaw": {"available": True, "score": 45.0, "label": "Needs Attention"},
            "nose": {"available": True, "score": 92.0, "label": "Excellent"},
        }
        projected_potential = {
            "skin": ["Even out skin tone."],
            "jaw": ["Consider a more defined jaw routine."],
            "nose": ["Unused -- nose is not flagged."],
        }
        monkeypatch.setattr(
            "app.services.ai_visual_service.assemble_sections",
            lambda *a, **k: _fake_sections(feature_scores, projected_potential),
        )
        rows = _build_potential_rows(uuid.uuid4(), _FAKE_ANALYSIS)
        assert rows[0].attributes["priority_features"] == ["skin", "jaw"]
        assert rows[0].explanation == "Even out skin tone.; Consider a more defined jaw routine."

    def test_caps_at_three_priority_features(self, monkeypatch):
        feature_scores = {
            feature: {"available": True, "score": float(score), "label": "Needs Attention"}
            for feature, score in [("skin", 10), ("jaw", 20), ("nose", 30), ("chin", 40)]
        }
        projected_potential = {feature: [f"idea for {feature}"] for feature in feature_scores}
        monkeypatch.setattr(
            "app.services.ai_visual_service.assemble_sections",
            lambda *a, **k: _fake_sections(feature_scores, projected_potential),
        )
        rows = _build_potential_rows(uuid.uuid4(), _FAKE_ANALYSIS)
        assert rows[0].attributes["priority_features"] == ["skin", "jaw", "nose"]

    def test_accepts_fr025_structured_recommendation_items(self, monkeypatch):
        """FR-025 -- projected_potential items are structured objects for a
        newly-assembled report; this must extract `.text` rather than
        embedding the raw object repr into the explanation string."""
        feature_scores = {"skin": {"available": True, "score": 30.0, "label": "Needs Attention"}}
        projected_potential = {"skin": [{"text": "Even out skin tone.", "cost": "$15-25"}]}
        monkeypatch.setattr(
            "app.services.ai_visual_service.assemble_sections",
            lambda *a, **k: _fake_sections(feature_scores, projected_potential),
        )
        rows = _build_potential_rows(uuid.uuid4(), _FAKE_ANALYSIS)
        assert rows[0].explanation == "Even out skin tone."

    def test_unavailable_or_non_needs_attention_features_are_skipped(self, monkeypatch):
        feature_scores = {
            "skin": {"available": False, "score": None, "label": None},
            "jaw": {"available": True, "score": 20.0, "label": "Needs Attention"},
        }
        projected_potential = {"jaw": ["Consider a defined jaw routine."]}
        monkeypatch.setattr(
            "app.services.ai_visual_service.assemble_sections",
            lambda *a, **k: _fake_sections(feature_scores, projected_potential),
        )
        rows = _build_potential_rows(uuid.uuid4(), _FAKE_ANALYSIS)
        assert rows[0].attributes["priority_features"] == ["jaw"]


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

    def test_potential_prompt_is_whole_face_and_cites_the_composed_suggestions(self):
        row = AiVisual(kind="potential", variation_index=0, name="Your Potential", explanation="Even out skin tone.")
        prompt = _build_prompt("potential", row)
        assert "whole face" in prompt.lower()
        assert "Even out skin tone." in prompt
        assert "identity" in prompt.lower()


def test_aging_steps_constant_matches_confirmed_cadence():
    assert _AGING_STEPS == ((31, "Near term"), (33, "Mid range"), (38, "Longer range"))
