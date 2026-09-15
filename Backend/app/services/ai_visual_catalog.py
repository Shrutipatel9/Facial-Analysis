"""Templated hairstyle/outfit variation catalog (FR-020a/b, Milestone 2
Phase 11) -- pure functions, no DB/AI dependency, same independently-
unit-testable posture as facial_assessment_service.py.

Per the user's explicit 2026-09-13 decision (see
D:\\zzz\\ai-visuals-hairstyle\\plans.md decision 1): variation "recipes"
(name/attributes/explanation) are a hand-written catalog, deterministically
ranked/selected using data facial_assessment_service.py already computes
(Face Shape label for hairstyle, Dimorphism label for outfit) -- not a new
AI text-generation call. Only the actual preview image is AI-generated.
This is a first-pass heuristic with no ground truth to validate against,
same posture as ASM-002/ASM-007/ASM-010 elsewhere in this project -- the
catalog entries beyond the 2-3 the source reference video actually showed
are a reasonable invention, not verified against any reference material.
"""

from dataclasses import dataclass, field

# Mirrors facial_assessment_service._classify_face_shape's return values.
_FACE_SHAPES: tuple[str, ...] = ("Oval", "Round", "Square", "Long/Oblong", "Heart", "Diamond")
# Mirrors facial_assessment_service._DIMORPHISM_LABEL_BANDS's labels.
_DIMORPHISM_LABELS: tuple[str, ...] = ("Hyper Feminine", "Feminine", "Moderate", "Masculine", "Hyper Masculine")


@dataclass(frozen=True)
class VariationArchetype:
    name: str
    attributes: dict[str, str]
    explanation: str
    suited_face_shapes: tuple[str, ...] = field(default_factory=tuple)
    suited_dimorphism_labels: tuple[str, ...] = field(default_factory=tuple)


HAIRSTYLE_CATALOG: tuple[VariationArchetype, ...] = (
    VariationArchetype(
        name="Soft Layered Bob",
        attributes={"Maintenance": "Low", "Layers": "Yes", "Parting": "Center", "Vibe": "Soft"},
        explanation=(
            "A rounded, chin-length silhouette with soft layers that gently narrows a fuller face and "
            "balances a rounder jawline -- an easy, low-maintenance everyday shape."
        ),
        suited_face_shapes=("Oval", "Round"),
    ),
    VariationArchetype(
        name="Long Face-Framing Layers",
        attributes={"Maintenance": "Medium", "Layers": "Yes", "Parting": "Side", "Vibe": "Romantic"},
        explanation=(
            "Long, softly graduated layers that curve inward at the jaw, softening a stronger jawline "
            "and adding width where an elongated face benefits from it most."
        ),
        suited_face_shapes=("Square", "Long/Oblong", "Heart"),
    ),
    VariationArchetype(
        name="Soft Updo Framing",
        attributes={"Maintenance": "Medium", "Layers": "No", "Parting": "Center", "Vibe": "Elegant"},
        explanation=(
            "A polished, swept-back style that keeps focus on the cheekbones and jawline -- flattering "
            "on a face with strong, well-balanced angles."
        ),
        suited_face_shapes=("Diamond", "Oval"),
    ),
    VariationArchetype(
        name="Textured Crop",
        attributes={"Maintenance": "Low", "Layers": "No", "Parting": "Side", "Vibe": "Modern"},
        explanation=(
            "A short, textured cut with volume on top -- adds vertical length to a wider or rounder "
            "face shape without extra bulk at the sides."
        ),
        suited_face_shapes=("Round", "Square"),
    ),
    VariationArchetype(
        name="Classic Side-Swept Bob",
        attributes={"Maintenance": "Low", "Layers": "Yes", "Parting": "Side", "Vibe": "Polished"},
        explanation=(
            "A side part draws the eye diagonally, softening a pointed chin while keeping a clean, "
            "polished everyday shape."
        ),
        suited_face_shapes=("Heart", "Oval"),
    ),
    VariationArchetype(
        name="Voluminous Curls",
        attributes={"Maintenance": "High", "Layers": "Yes", "Parting": "Center", "Vibe": "Bold"},
        explanation=(
            "Full, bouncy curls add width at the temples and cheeks -- a flattering counterbalance for "
            "a narrower or longer face shape."
        ),
        suited_face_shapes=("Long/Oblong", "Diamond"),
    ),
    VariationArchetype(
        name="Sleek Straight Lob",
        attributes={"Maintenance": "Medium", "Layers": "No", "Parting": "Center", "Vibe": "Sleek"},
        explanation=(
            "A straight, shoulder-length cut with a clean center part -- elongates a wider face while "
            "keeping a balanced, versatile length on an oval face."
        ),
        suited_face_shapes=("Square", "Oval"),
    ),
    VariationArchetype(
        name="Wispy Fringe Layers",
        attributes={"Maintenance": "Medium", "Layers": "Yes", "Parting": "Side", "Vibe": "Playful"},
        explanation=(
            "Soft, wispy fringe breaks up a broader forehead and softens a rounder face with a bit of "
            "movement at the front."
        ),
        suited_face_shapes=("Round", "Heart"),
    ),
    VariationArchetype(
        name="Long Layered Waves",
        attributes={"Maintenance": "High", "Layers": "Yes", "Parting": "Center", "Vibe": "Effortless"},
        explanation=(
            "Long, loose layers with natural wave add fullness at the jawline -- a versatile, "
            "effortless shape that suits a wide range of face proportions."
        ),
        suited_face_shapes=("Oval", "Diamond", "Long/Oblong"),
    ),
)

OUTFIT_CATALOG: tuple[VariationArchetype, ...] = (
    VariationArchetype(
        name="Minimalist Monochrome",
        attributes={"Occasion": "Everyday", "Formality": "Casual", "Palette": "Monochrome", "Vibe": "Clean"},
        explanation="A single-tone, clean-lined look that keeps the focus on natural presentation, no visual noise.",
        suited_dimorphism_labels=("Moderate", "Feminine"),
    ),
    VariationArchetype(
        name="Textured Layered",
        attributes={"Occasion": "Casual", "Formality": "Relaxed", "Palette": "Earth Tones", "Vibe": "Rugged"},
        explanation="Layered textures in warm, earthy tones for a relaxed, grounded everyday presentation.",
        suited_dimorphism_labels=("Masculine", "Hyper Masculine"),
    ),
    VariationArchetype(
        name="Tailored Structured Blazer",
        attributes={"Occasion": "Professional", "Formality": "Formal", "Palette": "Neutral", "Vibe": "Sharp"},
        explanation="A structured, sharply tailored silhouette suited to a professional or formal portrait setting.",
        suited_dimorphism_labels=("Masculine", "Moderate"),
    ),
    VariationArchetype(
        name="Soft Draped Layers",
        attributes={"Occasion": "Everyday", "Formality": "Casual", "Palette": "Pastel", "Vibe": "Soft"},
        explanation="Soft, draped fabric in gentle pastel tones for an approachable, everyday softness.",
        suited_dimorphism_labels=("Feminine", "Hyper Feminine"),
    ),
    VariationArchetype(
        name="Classic Crew Neck Layering",
        attributes={"Occasion": "Casual", "Formality": "Smart Casual", "Palette": "Neutral", "Vibe": "Timeless"},
        explanation="A timeless, easy-to-wear neutral layering combination that works across most everyday settings.",
        suited_dimorphism_labels=("Moderate", "Masculine"),
    ),
    VariationArchetype(
        name="Statement Color Block",
        attributes={"Occasion": "Social", "Formality": "Casual", "Palette": "Bold Color", "Vibe": "Playful"},
        explanation="A bold, color-blocked combination for a lively, social-occasion presentation.",
        suited_dimorphism_labels=("Hyper Feminine", "Feminine"),
    ),
    VariationArchetype(
        name="Structured Turtleneck",
        attributes={
            "Occasion": "Professional",
            "Formality": "Smart Casual",
            "Palette": "Dark Neutral",
            "Vibe": "Refined",
        },
        explanation="A refined, dark-neutral turtleneck silhouette for a polished professional presentation.",
        suited_dimorphism_labels=("Hyper Masculine", "Masculine"),
    ),
    VariationArchetype(
        name="Relaxed Knit Layers",
        attributes={"Occasion": "Everyday", "Formality": "Casual", "Palette": "Warm Neutral", "Vibe": "Relaxed"},
        explanation="Soft, warm-neutral knitwear for a relaxed, comfortable everyday look.",
        suited_dimorphism_labels=("Moderate", "Feminine"),
    ),
    VariationArchetype(
        name="Sharp Collared Shirt",
        attributes={"Occasion": "Professional", "Formality": "Formal", "Palette": "Cool Neutral", "Vibe": "Polished"},
        explanation="A crisp, cool-neutral collared shirt for a sharp, polished formal presentation.",
        suited_dimorphism_labels=("Masculine", "Hyper Masculine", "Moderate"),
    ),
)


def _score(archetype: VariationArchetype, *, face_shape: str | None, dimorphism_label: str | None) -> int:
    score = 0
    if face_shape is not None and face_shape in archetype.suited_face_shapes:
        score += 1
    if dimorphism_label is not None and dimorphism_label in archetype.suited_dimorphism_labels:
        score += 1
    return score


def select_variations(
    catalog: tuple[VariationArchetype, ...],
    *,
    face_shape: str | None,
    dimorphism_label: str | None,
    count: int = 5,
) -> list[VariationArchetype]:
    """Deterministic: ranks the catalog by suitability score (descending,
    ties broken by original catalog order for stability), returns the top
    `count`. The catalog is sized so this never runs short. Index 0 of the
    result is the best match -- the caller marks it `is_recommended`."""
    ranked = sorted(
        enumerate(catalog),
        key=lambda pair: (-_score(pair[1], face_shape=face_shape, dimorphism_label=dimorphism_label), pair[0]),
    )
    return [archetype for _, archetype in ranked[:count]]
