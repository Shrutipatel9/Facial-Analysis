"""Unit tests for app/services/ai_visual_catalog.py -- pure functions, no
DB/AI dependency, no fixtures needed."""

import pytest

from app.services.ai_visual_catalog import (
    HAIRSTYLE_CATALOG,
    OUTFIT_CATALOG,
    select_variations,
)


class TestSelectVariations:
    def test_returns_exactly_count_entries(self):
        result = select_variations(HAIRSTYLE_CATALOG, face_shape="Oval", dimorphism_label=None, count=5)
        assert len(result) == 5

    def test_entries_are_distinct(self):
        result = select_variations(HAIRSTYLE_CATALOG, face_shape="Round", dimorphism_label=None, count=5)
        names = [archetype.name for archetype in result]
        assert len(names) == len(set(names))

    def test_deterministic_for_same_inputs(self):
        first = select_variations(HAIRSTYLE_CATALOG, face_shape="Square", dimorphism_label=None, count=5)
        second = select_variations(HAIRSTYLE_CATALOG, face_shape="Square", dimorphism_label=None, count=5)
        assert [a.name for a in first] == [a.name for a in second]

    def test_matching_face_shape_ranks_first(self):
        # "Textured Crop" is suited to Round/Square only -- with face_shape="Round"
        # it must be selected among the top 5.
        result = select_variations(HAIRSTYLE_CATALOG, face_shape="Round", dimorphism_label=None, count=5)
        assert "Textured Crop" in [archetype.name for archetype in result]

    def test_unknown_face_shape_still_returns_count(self):
        result = select_variations(HAIRSTYLE_CATALOG, face_shape="Unknown Shape", dimorphism_label=None, count=5)
        assert len(result) == 5

    def test_none_face_shape_still_returns_count(self):
        result = select_variations(HAIRSTYLE_CATALOG, face_shape=None, dimorphism_label=None, count=5)
        assert len(result) == 5

    def test_outfit_catalog_ranks_by_dimorphism_label(self):
        result = select_variations(OUTFIT_CATALOG, face_shape=None, dimorphism_label="Hyper Masculine", count=5)
        assert len(result) == 5
        top_names = {a.name for a in result}
        # "Structured Turtleneck" is explicitly suited to Hyper Masculine -- must be selected.
        assert "Structured Turtleneck" in top_names

    @pytest.mark.parametrize("count", [1, 3, 5])
    def test_respects_requested_count(self, count):
        assert len(select_variations(HAIRSTYLE_CATALOG, face_shape="Oval", dimorphism_label=None, count=count)) == count


class TestCatalogContent:
    def test_hairstyle_catalog_has_at_least_five_entries(self):
        assert len(HAIRSTYLE_CATALOG) >= 5

    def test_outfit_catalog_has_at_least_five_entries(self):
        assert len(OUTFIT_CATALOG) >= 5

    def test_every_hairstyle_entry_has_four_attributes(self):
        for archetype in HAIRSTYLE_CATALOG:
            assert set(archetype.attributes.keys()) == {"Maintenance", "Layers", "Parting", "Vibe"}

    def test_every_outfit_entry_has_four_attributes(self):
        for archetype in OUTFIT_CATALOG:
            assert set(archetype.attributes.keys()) == {"Occasion", "Formality", "Palette", "Vibe"}

    def test_every_entry_has_a_non_empty_explanation(self):
        for archetype in (*HAIRSTYLE_CATALOG, *OUTFIT_CATALOG):
            assert archetype.explanation.strip() != ""
