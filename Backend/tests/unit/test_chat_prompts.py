from app.services.chat_prompts import build_suggested_prompts


def _sections(**overrides):
    base = {
        "feature_scores": {},
        "facial_assessments": {},
    }
    base.update(overrides)
    return base


class TestBuildSuggestedPrompts:
    def test_always_includes_the_two_generic_prompts(self):
        prompts = build_suggested_prompts(_sections())
        assert "What are my top improvement priorities?" in prompts
        assert "How should I track progress over 30 days?" in prompts

    def test_includes_lowest_scoring_feature_when_available(self):
        sections = _sections(
            feature_scores={
                "skin": {"available": True, "score": 38.0, "label": "Needs Attention"},
                "eyes": {"available": True, "score": 84.0, "label": "Excellent"},
                "hair": {"available": False, "score": None, "label": None},
            }
        )
        prompts = build_suggested_prompts(sections)
        assert any("skin" in prompt for prompt in prompts)
        assert not any("eyes" in prompt for prompt in prompts)

    def test_includes_face_shape_prompt_when_available(self):
        sections = _sections(facial_assessments={"face_shape": {"available": True, "label": "Oval"}})
        prompts = build_suggested_prompts(sections)
        assert any("oval" in prompt.lower() for prompt in prompts)

    def test_omits_face_shape_prompt_when_unavailable(self):
        sections = _sections(facial_assessments={"face_shape": {"available": False, "label": None}})
        prompts = build_suggested_prompts(sections)
        assert not any("face shape" in prompt.lower() for prompt in prompts)

    def test_degrades_to_just_the_two_generic_prompts_when_nothing_available(self):
        prompts = build_suggested_prompts(_sections())
        assert len(prompts) == 2

    def test_never_returns_more_than_four(self):
        sections = _sections(
            feature_scores={"skin": {"available": True, "score": 38.0, "label": "Needs Attention"}},
            facial_assessments={"face_shape": {"available": True, "label": "Oval"}},
        )
        prompts = build_suggested_prompts(sections)
        assert len(prompts) <= 4
