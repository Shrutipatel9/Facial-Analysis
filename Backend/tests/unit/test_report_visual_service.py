from app.services.report_visual_service import _select_source_image


class TestSelectSourceImage:
    """2026-09-17, user-reported: an "eyes" AI before/after visual came
    back showing the nose instead. Root cause: generate_all_feature_visuals
    fell back to the full, uncropped front photo whenever a feature had no
    crop of its own, so the model received the whole face as the source
    image while the prompt still named one specific feature (e.g. "this
    photo of the person's eyes"), with no real anchor for which region to
    edit. _select_source_image must never fall back to the front photo."""

    def test_prefers_a_persisted_crop_over_a_freshly_extracted_one(self):
        result = _select_source_image(
            "eyes", persisted_crops={"eyes": b"persisted-crop"}, crops={"eyes": b"fresh-crop"}
        )
        assert result == b"persisted-crop"

    def test_falls_back_to_a_freshly_extracted_crop_when_nothing_is_persisted(self):
        result = _select_source_image("eyes", persisted_crops={}, crops={"eyes": b"fresh-crop"})
        assert result == b"fresh-crop"

    def test_returns_none_when_no_crop_exists_for_this_feature_at_all(self):
        """The regression itself: previously this returned the full front
        photo instead of None."""
        result = _select_source_image("eyes", persisted_crops={}, crops={"eyes": None})
        assert result is None

    def test_returns_none_when_the_feature_is_missing_from_both_dicts(self):
        result = _select_source_image("ears", persisted_crops={"eyes": b"other-crop"}, crops={"eyes": b"other-crop"})
        assert result is None

    def test_never_returns_a_different_features_crop(self):
        result = _select_source_image("nose", persisted_crops={}, crops={"eyes": b"eyes-crop", "nose": None})
        assert result is None
