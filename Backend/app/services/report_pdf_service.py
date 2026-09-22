"""Branded PDF export (FR-013) -- built with ReportLab, a pure-Python
dependency with no system-level requirements (chosen over WeasyPrint/
Playwright specifically for portable, dependency-free installs across dev
machines -- see D:\\zzz\\report-generation\\plans.md). Renders a Report's
already-assembled `sections` JSON plus its per-feature cropped images
(see facial_measurement_service.extract_feature_crops); does not re-derive
or re-fetch anything else.

Page structure now follows docs/report_template.md v3.0 §2's exact page-
by-page content map (client-authorized 2026-09-15, superseding the prior
round's structure): Cover, Disclaimer & Privacy Policy, Introduction
(intro + Limitations + Contents list, 2-column), Understanding the Results
(4 fixed numbered principles), "{Subject}'s Protocol" overview (framing
prose + the fixed 11-feature checklist), Facial Assessments (FR-018 --
kept as a bonus page; not part of the client reference's own page list,
but not contradicted by it either), one page per feature (Eyebrows+Eyes
share a single page, matching report_design_spec.md §9.2's only such
case), Closing Recommendations (4-part synthesis, 2-column), and a bonus
Appendix. Per this round's explicitly deferred scope (see the report
redesign plan), this does NOT attempt: the per-feature named sub-sections
report_design_spec.md §9.2 lists for every feature (would need restructuring
ai_narrative_service.py's prompt per-feature, not just reusing existing
data -- existing narrative/strengths/areas_of_note/recommendation_ideas
are reused as-is, with headings relabeled toward the spec's sub-section
names only where a clean 1:1 mapping exists without inventing content),
profile/annotated/composite photo panels, or the second 11-axis radar
chart. Colors and the FaceIQ wordmark still match the actual app theme
(frontend/src/app/globals.css's `:root` tokens, converted from OKLCH to
sRGB hex once below) and the app's own two-weight wordmark styling
(Logo.tsx: "Face" semibold + "IQ" black) rather than the reference's own
palette/branding -- unchanged, only page structure/content moved.
"""

import io
import math
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import Image as RLImage

from app.models.report import Report
from app.models.user import User
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.report_assembly_service import recommendation_text

# Geist (SIL Open Font License -- app/assets/fonts/OFL.txt), the same
# typeface the web app uses (frontend/src/app/globals.css's --font-sans /
# next/font/google's Geist import) -- statically instanced once from
# Google Fonts' variable-font source at the weights this report actually
# uses (fonttools varLib.instancer; see the module docstring's design-round
# note) rather than embedded as a variable font, since ReportLab has no
# variable-font axis support and needs one static face per weight.
# Registered under the family name "Geist" (not a per-weight name) with
# registerFontFamily below so inline `<b>...</b>` markup inside a Paragraph
# resolves to the bold face automatically, the same as it would for a
# built-in base-14 font.
_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
for _weight_name in ("Regular", "Medium", "SemiBold", "Bold", "Black"):
    pdfmetrics.registerFont(TTFont(f"Geist-{_weight_name}", str(_FONT_DIR / f"Geist-{_weight_name}.ttf")))
pdfmetrics.registerFontFamily("Geist", normal="Geist-Regular", bold="Geist-Bold")

# App theme tokens (frontend/src/app/globals.css `:root`), converted from
# OKLCH to sRGB hex -- keeps the PDF visually consistent with the web app
# rather than an independent palette.
_PAPER = colors.HexColor("#F1F4F6")  # matches (protected)/layout.tsx's page-shell background
_INK = colors.HexColor("#14191A")  # --foreground
_INK_MUTED = colors.HexColor("#5A6668")  # --muted-foreground
_ACCENT = colors.HexColor("#4E7A82")  # --primary
_RECESSED = colors.HexColor("#D7E0E2")  # --border
_CALLOUT_BG = colors.HexColor("#E7EEF0")  # light tint of _ACCENT, for the per-feature Summary callout box
# A visibly different tint from _CALLOUT_BG -- deliberately so the "At a
# Glance" attribute box (AI-classified qualitative readings) never reads as
# the same kind of element as the Measurements table (raw CV numbers) above
# it or the Summary callout (closing synthesis) below it on the same page.
_ATTRIBUTE_BG = colors.HexColor("#F2EFE7")
_HAIR_LOSS_STAGE_FILL = colors.HexColor("#F6E9DE")  # light tint of a caution/amber tone, current-stage marker only

_PAGE_SIZE = LETTER
_MARGIN = 0.85 * inch
_CONFIDENTIALITY_NOTE = "Personal and confidential — generated for your individual use."
# PDF-only static copy for the Disclaimer & Privacy Policy page --
# deliberately NOT threaded through report_assembly_service.py/sections or
# the API schema, since nothing on the frontend needs this text this round
# (keeps the blast radius of this addition contained to this file).
# report_template.md v3.0 §4 -- standing, legally-reviewed copy, never
# AI-generated, never omitted or shortened. Distinct from `_LIMITATIONS`
# below (what can affect *measurement accuracy* -- now on the Introduction
# page instead, per §5) -- this is the platform's own standing disclaimer.
_DISCLAIMER_POLICY = (
    "This report is an AI-assisted facial appearance analysis, informational and cosmetic in "
    "nature. It is not a medical diagnosis, clinical assessment, surgical plan, or disease-"
    "detection tool. Recommendations throughout this report are general and cosmetic, not a "
    "course of treatment. Numeric scores describe measured facial geometry only — they are never "
    "an attractiveness or beauty judgment. Any AI-generated Before/After or Potential imagery in "
    "this report is a simulation, illustrative only, with no guaranteed real-world outcome. Any "
    "decision about treatment, in-clinic procedures, or prescription products should always be "
    "made together with a qualified professional, not from this report alone."
)
_PRIVACY_POLICY = (
    "Your uploaded photos and questionnaire answers are used solely to generate this report for "
    "your own account. We do not sell your photos or personal data, and we do not use them to "
    "train shared AI models. Supplied images and video are retained for a bounded window (up to "
    "1 year) for reference purposes; once modified by the platform, an image is stored as a whole, "
    "not disaggregated into its component edits. Photos and analysis results otherwise remain "
    "available for as long as your account is active, so you can access your report history; you "
    "may request deletion at any time. This platform uses cookies and basic analytics to operate "
    "and improve the service — see the full privacy policy for details."
)
# Cover, Disclaimer & Privacy, Introduction, Understanding the Results,
# "{Subject}'s Protocol" overview, Facial Assessments -- always exactly one
# page each (fixed-length static copy + a short synthesis paragraph or an
# 11-row/5-row table that comfortably fits one Letter page), so front-matter
# page count is a safe compile-time constant rather than something computed
# at render time. report_template.md v3.0's page map folds the prior
# round's separate "About This Report" and "Table of Contents" pages into
# one combined Introduction page, so this drops 8->6, then 6->7 when the
# Overview page (_overview_flowables) was added per client instruction
# 2026-09-15.
# tests/integration/test_report_flow.py's TestReportPdf::test_pdf_is_not_
# duplicated imports this constant directly (rather than hardcoding its own
# copy of the number, a real drift this constant already caused once) to
# assert the rendered page count -- so it self-updates whenever this
# constant changes. Body pages (features onward) are NOT a similarly safe
# compile-time assumption -- a feature's AI-generated narrative can
# overflow onto a second physical page for a long real account even though
# the test suite's short synthetic fixtures never do -- so their Table of
# Contents labels are resolved via a two-pass render (_PageMarker /
# render_pdf's docstring), not arithmetic. Overview shares that same risk
# in principle (its Priority Features list and Treatment Protocol length
# both vary per report) but its content was sized to comfortably fit one
# page in practice, unlike feature pages where overflow is common with
# real (non-synthetic) narrative length.
_FRONT_MATTER_PAGE_COUNT = 7

# Named front-matter page positions (1-indexed), matching render_pdf()'s
# exact story order below -- used by _introduction_flowables' Contents list
# so its page-number arithmetic never hardcodes a bare integer. Keep this
# literally in sync with render_pdf()'s story.extend(...) sequence; there
# is no automated check for that (see the comment on _FRONT_MATTER_PAGE_COUNT
# above).
_PAGE_UNDERSTANDING = 4
_PAGE_PROTOCOL_OVERVIEW = 5
_PAGE_FACIAL_ASSESSMENTS = 6
_PAGE_OVERVIEW = 7
assert _PAGE_OVERVIEW == _FRONT_MATTER_PAGE_COUNT  # the last front-matter page is always this constant


def _to_roman(num: int) -> str:
    values = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    result: list[str] = []
    for value, symbol in values:
        while num >= value:
            result.append(symbol)
            num -= value
    return "".join(result)


def _draw_wordmark(canvas: Canvas, x: float, y: float, size: float, center: bool = False) -> None:
    """Renders "FaceIQ" matching Logo.tsx exactly: "Face" in Geist SemiBold
    (font-semibold, 600) + "IQ" in Geist Black (font-black, 900) -- both
    real static weights of the same font the web app uses, not a faux-bold
    approximation (the previous round's double-strike trick was a
    workaround for base-14 Helvetica having no 900 weight at all)."""
    canvas.saveState()
    canvas.setFillColor(_INK)
    face_font, iq_font = "Geist-SemiBold", "Geist-Black"
    face_width = canvas.stringWidth("Face", face_font, size)
    iq_width = canvas.stringWidth("IQ", iq_font, size)
    total_width = face_width + iq_width
    start_x = x - total_width / 2 if center else x

    canvas.setFont(face_font, size)
    canvas.drawString(start_x, y, "Face")
    canvas.setFont(iq_font, size)
    canvas.drawString(start_x + face_width, y, "IQ")
    canvas.restoreState()


# Static face-mesh landmark layout for _draw_face_scan_icon, as fractions
# of face_r (see that function) -- same visual language as the animated
# web scan glyph (frontend/src/components/auth/FacialScanVisual.tsx:
# viewfinder corners + a face outline + a connected landmark mesh + dots
# at each landmark), reduced to a small, legible point set since this
# icon renders at ~0.85in and the web version's full 26-point mesh would
# just be visual mud at that size. A PDF is static by nature, so this is
# the animation's "settled" end-state (dots fully opaque, mesh fully
# drawn) rather than an attempt to animate anything.
_FACE_MESH_POINTS = {
    "left_eyebrow": (-0.34, 0.40),
    "right_eyebrow": (0.34, 0.40),
    "left_eye": (-0.30, 0.24),
    "right_eye": (0.30, 0.24),
    "nose": (0.0, 0.0),
    "mouth_left": (-0.20, -0.38),
    "mouth_right": (0.20, -0.38),
    "chin": (0.0, -0.80),
    "jaw_left": (-0.46, -0.50),
    "jaw_right": (0.46, -0.50),
}
_FACE_MESH_LINES = (
    ("left_eyebrow", "left_eye"),
    ("right_eyebrow", "right_eye"),
    ("left_eye", "nose"),
    ("right_eye", "nose"),
    ("nose", "mouth_left"),
    ("nose", "mouth_right"),
    ("mouth_left", "mouth_right"),
    ("mouth_left", "jaw_left"),
    ("mouth_right", "jaw_right"),
    ("jaw_left", "chin"),
    ("jaw_right", "chin"),
    ("left_eye", "jaw_left"),
    ("right_eye", "jaw_right"),
)


def _draw_face_scan_icon(canvas: Canvas, center_x: float, center_y: float, size: float) -> None:
    """Vector face-scan glyph (viewfinder corners + a face outline + a
    connected landmark mesh) in the brand ink/accent colors -- the static
    counterpart of the animated FacialScanVisual used throughout the web
    app, so the report's cover carries the same icon identity, not an
    unrelated simpler glyph. See _FACE_MESH_POINTS/_FACE_MESH_LINES above
    for the layout."""
    canvas.saveState()
    canvas.setStrokeColor(_ACCENT)
    canvas.setLineWidth(1.6)
    half = size / 2
    corner = size * 0.22
    left, right = center_x - half, center_x + half
    top, bottom = center_y + half, center_y - half
    for cx, cy, dx, dy in ((left, top, 1, -1), (right, top, -1, -1), (left, bottom, 1, 1), (right, bottom, -1, 1)):
        canvas.line(cx, cy, cx + dx * corner, cy)
        canvas.line(cx, cy, cx, cy + dy * corner)

    face_r = size * 0.32
    points_px = {
        name: (center_x + fx * face_r, center_y + fy * face_r) for name, (fx, fy) in _FACE_MESH_POINTS.items()
    }

    canvas.setStrokeColor(_INK)
    canvas.setStrokeAlpha(0.85)
    canvas.setLineWidth(1.1)
    canvas.ellipse(
        center_x - face_r * 0.78, center_y - face_r * 1.02, center_x + face_r * 0.78, center_y + face_r * 1.02
    )

    canvas.setLineWidth(0.5)
    canvas.setStrokeAlpha(0.4)
    for start_name, end_name in _FACE_MESH_LINES:
        sx, sy = points_px[start_name]
        ex, ey = points_px[end_name]
        canvas.line(sx, sy, ex, ey)

    canvas.setFillColor(_INK)
    canvas.setFillAlpha(1)
    dot_r = size * 0.028
    for px, py in points_px.values():
        canvas.circle(px, py, dot_r, stroke=0, fill=1)

    canvas.restoreState()

# Explicit overrides for metric keys that .title()-casing alone would
# render awkwardly (facial_measurement_service.py's _measure_* functions
# are the source of every key that appears here).
_METRIC_LABEL_OVERRIDES = {
    "mean_r": "Mean Red",
    "mean_g": "Mean Green",
    "mean_b": "Mean Blue",
}


def _humanize_metric_key(key: str) -> str:
    if key in _METRIC_LABEL_OVERRIDES:
        return _METRIC_LABEL_OVERRIDES[key]
    if key.endswith("_px"):
        return f"{key[: -len('_px')].replace('_', ' ').title()} (px)"
    if key.endswith("_deg"):
        return f"{key[: -len('_deg')].replace('_', ' ').title()} (°)"
    return key.replace("_", " ").title()


_FEATURE_LABELS = {
    "hair": "Hair",
    "eyebrows": "Brows",
    "eyes": "Eyes",
    "nose": "Nose",
    "cheeks": "Cheeks",
    "jaw": "Jaw",
    "lips": "Lips",
    "chin": "Chin",
    "skin": "Skin",
    "neck": "Neck",
    "ears": "Ears",
}

# Same wording already established in frontend/src/components/report/
# sections/ProtocolSection.tsx's TIERS array -- kept identical so a feature's
# tier reads the same on the PDF and on /report's Protocol section.
_TIER_LABELS = {
    "at_home": "At-Home / Lifestyle",
    "otc_skincare": "OTC / Skincare-Active",
    "in_clinic": "In-Clinic (Optional)",
}


class _AccentRule(Flowable):
    """A short brand-teal rule under a page's h1 -- a small structural
    accent (not new content) so a page's primary heading is anchored by
    color, not just size/weight, echoing the app's own use of _ACCENT as a
    focal color rather than a purely monochrome heading. Sized to be
    height-neutral against the previous plain h1 spacing (see _heading1)."""

    def __init__(self, width: float = 0.5 * inch, thickness: float = 2.2, color: Any = None) -> None:
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color or _ACCENT
        self.height = thickness

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return (self.width, self.height)

    def draw(self) -> None:
        self.canv.saveState()
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.thickness, fill=1, stroke=0)
        self.canv.restoreState()


def _heading1(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Every page-level h1 goes through this (not a bare Paragraph) so the
    accent-rule treatment is applied once, consistently, everywhere --
    see _AccentRule's docstring for why the rule + spacer below are sized
    to land at the same total height as the old plain-h1 spaceAfter."""
    return [Paragraph(text, styles["h1"]), _AccentRule(), Spacer(1, 5)]


def _styles() -> dict[str, ParagraphStyle]:
    """Every style below sets fontName explicitly to a Geist face rather
    than inheriting getSampleStyleSheet()'s Helvetica default -- Geist is
    the app's own typeface (see this module's font-registration block up
    top), and the weight chosen per style is a deliberate hierarchy (Bold
    for primary headings, SemiBold for secondary ones and callout labels,
    Medium for small emphasis/label text, Regular for body copy) rather
    than leaning on size alone to separate them. "attribute_line" is the
    one body-weight style that uses inline `<b>` markup (see
    _attributes_flowables) -- registerFontFamily above lets ReportLab
    resolve a `<b>` span back to Geist-Bold from its base Geist-Regular
    fontName automatically, the same as it would for a built-in font."""
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Geist-Bold",
            textColor=_INK,
            fontSize=27,
            leading=31,
            alignment=TA_CENTER,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName="Geist-Medium",
            textColor=_ACCENT,
            fontSize=13,
            alignment=TA_CENTER,
            spaceBefore=6,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontName="Geist-Regular",
            textColor=_INK_MUTED,
            fontSize=9,
            alignment=TA_CENTER,
            spaceBefore=18,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Geist-Bold", textColor=_INK, fontSize=19, spaceAfter=2
        ),
        "principle_number": ParagraphStyle(
            "PrincipleNumber",
            parent=base["Normal"],
            fontName="Geist-Bold",
            textColor=_ACCENT,
            fontSize=16,
            leading=18,
            spaceBefore=6,
        ),
        # spaceBefore/spaceAfter/leading tightened twice now from the
        # original values (10/4 and 14/8): once for the Summary callout box,
        # and again here for the "At a Glance" attributes card + Hair Loss
        # scale added this round -- both eat into the same per-feature page
        # budget report_design_spec.md v3.0 §9.1 fixes at exactly one
        # physical page per feature. Applied globally (not per-feature)
        # since the difference is barely perceptible and keeps every page's
        # styling uniform.
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Geist-SemiBold",
            textColor=_INK,
            fontSize=13,
            spaceBefore=6,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Geist-Regular", textColor=_INK, fontSize=9.5, leading=12.5,
            spaceAfter=5,
        ),
        "muted": ParagraphStyle(
            "Muted", parent=base["BodyText"], fontName="Geist-Regular", textColor=_INK_MUTED, fontSize=8.5, leading=12
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Geist-Regular",
            textColor=_INK_MUTED,
            fontSize=8,
            leading=11,
            spaceAfter=6,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", parent=base["BodyText"], fontName="Geist-Regular", textColor=_INK, fontSize=9, leading=12.5
        ),
        "table_head": ParagraphStyle(
            "TableHead", parent=base["BodyText"], fontName="Geist-SemiBold", textColor=_ACCENT, fontSize=8.5,
            leading=12,
        ),
        "toc_entry": ParagraphStyle(
            "TocEntry", parent=base["BodyText"], fontName="Geist-Medium", textColor=_INK, fontSize=10.5, leading=18
        ),
        "toc_page": ParagraphStyle(
            "TocPage",
            parent=base["BodyText"],
            fontName="Geist-Regular",
            textColor=_INK_MUTED,
            fontSize=10.5,
            leading=18,
            alignment=TA_CENTER,
        ),
        "tier_caption": ParagraphStyle(
            "TierCaption", parent=base["BodyText"], fontName="Geist-Medium", textColor=_ACCENT, fontSize=8.5,
            leading=12, spaceAfter=4,
        ),
        "callout_heading": ParagraphStyle(
            "CalloutHeading", parent=base["Heading2"], fontName="Geist-SemiBold", textColor=_INK, fontSize=11,
            spaceAfter=3,
        ),
        "callout_body": ParagraphStyle(
            "CalloutBody", parent=base["BodyText"], fontName="Geist-Regular", textColor=_INK, fontSize=9.5,
            leading=13,
        ),
        "attribute_line": ParagraphStyle(
            "AttributeLine", parent=base["BodyText"], fontName="Geist-Regular", textColor=_INK, fontSize=9.5,
            leading=13, spaceAfter=3,
        ),
        # Overview page (_overview_flowables) -- mirrors HomeOverviewScreen.tsx's
        # StatRow/PriorityFeaturesCard/TreatmentProtocolPanel typography scale,
        # condensed for print.
        "stat_label": ParagraphStyle(
            "StatLabel", parent=base["Normal"], fontName="Geist-SemiBold", textColor=_INK_MUTED, fontSize=7.5,
            leading=10,
        ),
        "stat_value": ParagraphStyle(
            "StatValue", parent=base["Normal"], fontName="Geist-Bold", textColor=_INK, fontSize=17, leading=20,
            spaceBefore=2,
        ),
        "stat_value_accent": ParagraphStyle(
            "StatValueAccent", parent=base["Normal"], fontName="Geist-Bold", textColor=_ACCENT, fontSize=17,
            leading=20, spaceBefore=2,
        ),
        "priority_name": ParagraphStyle(
            "PriorityName", parent=base["Normal"], fontName="Geist-SemiBold", textColor=_INK, fontSize=9.5,
            leading=12,
        ),
        "priority_finding": ParagraphStyle(
            "PriorityFinding", parent=base["Normal"], fontName="Geist-Regular", textColor=_INK_MUTED, fontSize=8,
            leading=11, spaceAfter=2,
        ),
        "phase_title": ParagraphStyle(
            "PhaseTitle", parent=base["Normal"], fontName="Geist-SemiBold", textColor=_INK, fontSize=9.5, leading=12
        ),
        "phase_subtitle": ParagraphStyle(
            "PhaseSubtitle", parent=base["Normal"], fontName="Geist-Regular", textColor=_INK_MUTED, fontSize=7.5,
            leading=10, spaceAfter=3,
        ),
        "phase_bullet": ParagraphStyle(
            "PhaseBullet", parent=base["BodyText"], fontName="Geist-Regular", textColor=_INK, fontSize=8.5,
            leading=11.5, spaceAfter=2,
        ),
    }


def _scaled_image(image_bytes: bytes, max_width: float, max_height: float) -> RLImage:
    with PILImage.open(io.BytesIO(image_bytes)) as im:
        w, h = im.size
    scale = min(max_width / w, max_height / h, 1.0)
    return RLImage(io.BytesIO(image_bytes), width=w * scale, height=h * scale)


def _framed_image(image_bytes: bytes, max_width: float, max_height: float) -> Table:
    """A scaled photo in a thin frame sized to its own rendered dimensions,
    not the bounding box it was fit into -- a bare RLImage inside a wider
    box otherwise floats with the page's paper-colored background showing
    on whichever side the photo's aspect ratio doesn't fill, which reads as
    an unstyled gap rather than a deliberate crop. A snug 1pt border turns
    every photo into a small, consistent "card" instead."""
    image = _scaled_image(image_bytes, max_width, max_height)
    table = Table([[image]], colWidths=[image.drawWidth], rowHeights=[image.drawHeight])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, _RECESSED),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


class _ReportCanvas(Canvas):
    """Buffers pages so the footer's page number is known once every
    flowable has been laid out -- this defers drawing it until save().

    Numbering is two-part, like a printed book: the fixed front-matter
    pages (cover, about, understanding, overview -- always exactly
    `_FRONT_MATTER_PAGE_COUNT`) show roman numerals, then the main body
    (feature sections onward) restarts at arabic "1". Every page gets a
    number now, including the cover, which previously had no footer at
    all."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        # NOTE: deliberately does NOT call super().showPage() here -- that
        # would finalize this page into the document immediately (without a
        # footer), and save() below would then finalize a *second* copy of
        # every page (this time with a footer), doubling every page in the
        # output PDF. self._startPage() only resets the canvas's internal
        # state for the next page; save() is the sole place a page actually
        # gets added to the document, exactly once each, with its footer
        # already drawn. This mirrors ReportLab's own documented
        # NumberedCanvas recipe for deferred page-count footers.
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        for index, state in enumerate(self._saved_states, start=1):
            self.__dict__.update(state)
            self._draw_footer(index)
            super().showPage()
        super().save()

    def current_page_number(self) -> int:
        """The 1-indexed physical page currently being drawn on -- every
        prior page has already been buffered into `_saved_states` via
        showPage() above, so its length is exactly the count of pages
        completed so far. Used by _PageMarker to record real page numbers
        for the Table of Contents (see render_pdf's two-pass docstring)."""
        return len(self._saved_states) + 1

    def _draw_footer(self, page_number: int) -> None:
        width, _ = _PAGE_SIZE
        if page_number <= _FRONT_MATTER_PAGE_COUNT:
            label = _to_roman(page_number)
        else:
            label = str(page_number - _FRONT_MATTER_PAGE_COUNT)
        self.saveState()
        self.setFont("Geist-Medium", 8)
        self.setFillColor(_INK_MUTED)
        self.drawRightString(width - _MARGIN, 0.55 * inch, label)
        self.restoreState()


class _PageMarker(Flowable):
    """Zero-size flowable placed at the start of a Table-of-Contents-tracked
    section (a feature page, Recommendations, Appendix). When drawn, it
    records the physical page it landed on into `page_numbers[name]` via
    _ReportCanvas.current_page_number() -- see render_pdf's two-pass
    docstring for why this replaced a plain 1-page-per-feature arithmetic
    assumption."""

    def __init__(self, name: str, page_numbers: dict[str, int]) -> None:
        super().__init__()
        self.name = name
        self.page_numbers = page_numbers
        self.width = 0
        self.height = 0

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return (0, 0)

    def draw(self) -> None:
        canv = self.canv
        if isinstance(canv, _ReportCanvas):
            self.page_numbers[self.name] = canv.current_page_number()


def _draw_page_background(canvas: Canvas, _doc: Any) -> None:
    width, height = _PAGE_SIZE
    canvas.saveState()
    canvas.setFillColor(_PAPER)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.restoreState()


def _draw_header(canvas: Canvas, _doc: Any) -> None:
    width, height = _PAGE_SIZE
    canvas.saveState()
    _draw_wordmark(canvas, _MARGIN, height - 0.63 * inch, size=11)
    canvas.setFont("Geist-Regular", 9)
    canvas.setFillColor(_INK_MUTED)
    canvas.drawRightString(width - _MARGIN, height - 0.6 * inch, "Facial Analysis Report")
    canvas.setStrokeColor(_RECESSED)
    canvas.setLineWidth(0.75)
    canvas.line(_MARGIN, height - 0.72 * inch, width - _MARGIN, height - 0.72 * inch)
    canvas.restoreState()


def _on_cover_page(canvas: Canvas, doc: Any) -> None:
    _draw_page_background(canvas, doc)
    width, _height = _PAGE_SIZE
    _draw_face_scan_icon(canvas, width / 2, 9.35 * inch, size=0.85 * inch)
    _draw_wordmark(canvas, width / 2, 8.35 * inch, size=30, center=True)


def _on_content_page(canvas: Canvas, doc: Any) -> None:
    _draw_page_background(canvas, doc)
    _draw_header(canvas, doc)


def render_pdf(
    report: Report,
    user: User,
    images: dict[str, bytes] | None = None,
    visuals: dict[str, bytes] | None = None,
    front_photo: bytes | None = None,
) -> bytes:
    """`visuals` (Milestone 2, FR-022) is already filtered to only
    status="generated" rows by report_service._load_all_feature_visuals --
    this function never checks a status string itself, a feature simply
    gets the before/after treatment if and only if its bytes are present
    here, exactly the same "presence = available" convention `images`
    already uses for crops.

    Renders twice. A feature's AI-generated narrative occasionally overflows
    its page onto a second physical page (longer real accounts than the
    synthetic fixtures used during development do this for Nose/Skin, for
    example) -- once that happens, every later section's real page number
    no longer matches a simple 1-page-per-feature arithmetic count, which
    the Table of Contents used before this fix. Pass 1 renders the full
    document with placeholder TOC digits purely to let each section's
    _PageMarker record its real page number (via _ReportCanvas.
    current_page_number()); pass 2 re-renders with those real numbers baked
    into the TOC. Both passes lay out identically apart from the TOC page's
    own digits, which don't change that page's own length, so pass 1's
    recorded numbers stay valid for pass 2."""
    images = images or {}
    visuals = visuals or {}
    sections = report.sections
    styles = _styles()
    generated_label = f"Generated {report.created_at.strftime('%B %d, %Y')}"

    page_numbers: dict[str, int] = {}
    _build_pdf(
        report, sections, styles, generated_label, images, visuals, page_numbers, toc_page_numbers=None,
        front_photo=front_photo,
    )
    return _build_pdf(
        report, sections, styles, generated_label, images, visuals, page_numbers, toc_page_numbers=page_numbers,
        front_photo=front_photo,
    )


def _build_pdf(
    report: Report,
    sections: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    generated_label: str,
    images: dict[str, bytes],
    visuals: dict[str, bytes],
    record_into: dict[str, int],
    toc_page_numbers: dict[str, int] | None,
    front_photo: bytes | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=_PAGE_SIZE,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=1.0 * inch,
        bottomMargin=0.9 * inch,
        title="FaceIQ Facial Analysis Report",
    )

    story: list[Any] = []
    story.extend(_cover_flowables(styles, report, generated_label))
    story.append(PageBreak())
    story.extend(_disclaimer_flowables(styles))
    story.append(PageBreak())
    story.extend(_introduction_flowables(styles, sections, toc_page_numbers))
    story.append(PageBreak())
    story.extend(_understanding_flowables(styles))
    story.append(PageBreak())
    story.extend(_protocol_overview_flowables(styles, sections, front_photo))
    story.append(PageBreak())
    story.extend(_facial_assessments_flowables(styles, sections))
    story.append(PageBreak())
    story.extend(_overview_flowables(styles, sections))
    story.append(PageBreak())

    features = sections.get("features", {})
    # Explicit client instruction (2026-09-15): every one of the 11
    # features always starts on its own fresh physical page, no exceptions
    # -- including Eyebrows/Eyes (previously a shared page) and the
    # transition into Closing Recommendations. A feature whose narrative
    # overflows onto a second physical page is accepted as-is rather than
    # optimized away (see render_pdf's two-pass docstring for why that
    # doesn't break the Table of Contents).
    for feature in ANALYSIS_FEATURES:
        story.append(_PageMarker(f"feature:{feature}", record_into))
        story.extend(
            _feature_flowables(
                styles, feature, features.get(feature, {}), images.get(feature), visuals.get(feature), sections
            )
        )
        story.append(PageBreak())

    story.append(_PageMarker("closing_recommendations", record_into))
    story.extend(_closing_recommendations_flowables(styles, sections))
    story.append(PageBreak())
    story.append(_PageMarker("appendix", record_into))
    story.extend(_appendix_flowables(styles, report))

    doc.build(
        story,
        onFirstPage=_on_cover_page,
        onLaterPages=_on_content_page,
        canvasmaker=_ReportCanvas,
    )
    return buffer.getvalue()


def _cover_flowables(styles: dict[str, ParagraphStyle], report: Report, generated_label: str) -> list[Any]:
    # The face-scan icon and "FaceIQ" wordmark are drawn directly on the
    # canvas (_on_cover_page) rather than as flowables here -- the
    # two-weight wordmark and vector icon aren't expressible as a Platypus
    # Paragraph. This spacer reserves the same vertical space they occupy.
    return [
        Spacer(1, 2.75 * inch),
        Paragraph("Facial Analysis Report", styles["cover_title"]),
        Paragraph("Your Report", styles["cover_subtitle"]),
        Paragraph(generated_label, styles["cover_meta"]),
        Paragraph(_CONFIDENTIALITY_NOTE, styles["cover_meta"]),
    ]


def _disclaimer_flowables(styles: dict[str, ParagraphStyle]) -> list[Any]:
    """report_template.md v3.0 §4 -- a dedicated 2-column Disclaimer /
    Privacy Policy page, pure standing legal copy (no per-report data).
    `sections["limitations"]` moved to the Introduction page (§5) below --
    this page no longer doubles as the "what affects measurement accuracy"
    text."""
    left_col = [
        Paragraph("Disclaimer Policy", styles["h2"]),
        Paragraph(_DISCLAIMER_POLICY, styles["body"]),
    ]
    right_col = [
        Paragraph("Privacy Policy", styles["h2"]),
        Paragraph(_PRIVACY_POLICY, styles["body"]),
    ]
    table = Table([[left_col, right_col]], colWidths=[2.85 * inch, 2.85 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, 0), 0.5, _RECESSED),
                ("LEFTPADDING", (1, 0), (1, 0), 14),
            ]
        )
    )
    return [*_heading1("Disclaimer & Privacy Policy", styles), Spacer(1, 8), table]


def _introduction_flowables(
    styles: dict[str, ParagraphStyle], sections: dict[str, Any], page_numbers: dict[str, int] | None
) -> list[Any]:
    """report_template.md v3.0 §5 -- a 2-column Introduction page: left is
    the method statement + Limitations (below a rule), right is the
    Contents list ("Understanding the Results" through "Closing
    Recommendations", plus this build's 2 bonus pages listed for honesty).
    Replaces the prior round's separate "About This Report" and "Table of
    Contents" pages -- folded into one, per the new page map."""
    limitations_text = sections.get("limitations") or (
        "This report is generated by an automated analysis of your submitted photos and "
        "questionnaire responses. It is not a medical diagnosis and has not been reviewed by a "
        "licensed professional."
    )
    left_col = [
        Paragraph(sections.get("intro", ""), styles["body"]),
        Spacer(1, 6),
        Paragraph("Limitations", styles["h2"]),
        Paragraph(limitations_text, styles["body"]),
    ]

    def _body_label(name: str) -> str:
        if page_numbers is None or name not in page_numbers:
            return "—"
        return str(page_numbers[name] - _FRONT_MATTER_PAGE_COUNT)

    contents_rows: list[list[Any]] = [
        [
            Paragraph("Understanding the Results", styles["toc_entry"]),
            Paragraph(_to_roman(_PAGE_UNDERSTANDING), styles["toc_page"]),
        ],
        [
            Paragraph("Your Protocol", styles["toc_entry"]),
            Paragraph(_to_roman(_PAGE_PROTOCOL_OVERVIEW), styles["toc_page"]),
        ],
        [
            Paragraph("Facial Assessments", styles["toc_entry"]),
            Paragraph(_to_roman(_PAGE_FACIAL_ASSESSMENTS), styles["toc_page"]),
        ],
        [
            Paragraph("Overview", styles["toc_entry"]),
            Paragraph(_to_roman(_PAGE_OVERVIEW), styles["toc_page"]),
        ],
    ]
    for feature in ANALYSIS_FEATURES:
        contents_rows.append(
            [
                Paragraph(_FEATURE_LABELS[feature], styles["toc_entry"]),
                Paragraph(_body_label(f"feature:{feature}"), styles["toc_page"]),
            ]
        )
    contents_rows.append(
        [
            Paragraph("Closing Recommendations", styles["toc_entry"]),
            Paragraph(_body_label("closing_recommendations"), styles["toc_page"]),
        ]
    )
    contents_rows.append(
        [Paragraph("Appendix", styles["toc_entry"]), Paragraph(_body_label("appendix"), styles["toc_page"])]
    )
    contents_table = Table(contents_rows, colWidths=[2.0 * inch, 0.7 * inch])
    contents_table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _RECESSED),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    right_col = [Paragraph("Contents", styles["h2"]), contents_table]

    table = Table([[left_col, right_col]], colWidths=[3.1 * inch, 2.6 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, 0), 0.5, _RECESSED),
                ("LEFTPADDING", (1, 0), (1, 0), 14),
            ]
        )
    )
    return [*_heading1("Introduction", styles), Spacer(1, 8), table]


# report_template.md v3.0 §6 -- 4 fixed, standing principles, identical
# across every report (not regenerated per report).
_UNDERSTANDING_PRINCIPLES = (
    (
        "These recommendations focus on facial health and harmony",
        "The recommendations in this report focus on markers of facial health and harmony, working "
        "with your existing features rather than trying to change what makes you distinctive.",
    ),
    (
        "FaceIQ does not rate attractiveness",
        "This platform does not rate attractiveness. The assessment highlights what works best for "
        "your own features using objective measurement, not a universal beauty standard.",
    ),
    (
        "Foundational and targeted guidance work together",
        "The protocol mixes foundational guidance (SPF, sleep, hydration) with more targeted "
        "recommendations — the fundamentals support the effectiveness of the more specific "
        "guidance, they aren't filler.",
    ),
    (
        "Everything here is informational and aesthetic only",
        "All recommendations are informational and aesthetic only; any in-clinic treatment or "
        "prescription product should always be discussed with a qualified medical professional.",
    ),
)


def _understanding_flowables(styles: dict[str, ParagraphStyle]) -> list[Any]:
    """report_template.md v3.0 §6 -- 4 large numbered principles, stacked
    vertically. Replaces the prior round's single free-text paragraph."""
    flowables: list[Any] = _heading1("Understanding the Results", styles)
    for index, (headline, body) in enumerate(_UNDERSTANDING_PRINCIPLES, start=1):
        flowables.append(Paragraph(f"{index:02d}", styles["principle_number"]))
        flowables.append(Paragraph(headline, styles["h2"]))
        flowables.append(Paragraph(body, styles["body"]))
        flowables.append(Spacer(1, 6))
    return flowables


def _protocol_overview_flowables(
    styles: dict[str, ParagraphStyle], sections: dict[str, Any], front_photo: bytes | None
) -> list[Any]:
    """report_template.md v3.0 §7 -- "{Subject}'s Protocol" overview page:
    what the protocol is for, an objective/non-comparative framing
    paragraph, and the fixed 11-feature "Projected potential" checklist
    (2 columns, no per-feature detail yet -- that's the feature pages
    below). Replaces the prior round's separate Overview (feature/at-a-
    glance table) and Overall Summary (closing-recommendations prose)
    pages. The reference's large top photo pair is half-deferred: there is
    no whole-face "potential" image to show as an "After" yet (that needs
    a new AI-generation capability this round doesn't add), but the
    subject's own uncropped front photo is real, already-uploaded evidence
    -- showing it here, honestly labeled (never implying a before/after
    pair that doesn't exist), is better than the mostly-blank page a text-
    only version of this page left. The second (11-axis, two-series) radar
    chart stays fully deferred -- it needs a per-feature "projected
    potential" numeric value this round doesn't compute (see the report
    redesign plan)."""
    photo_flowables: list[Any] = []
    if front_photo:
        photo_flowables = [
            _framed_image(front_photo, max_width=2.6 * inch, max_height=3.2 * inch),
            Paragraph("Your photo, as submitted for this analysis.", styles["caption"]),
            Spacer(1, 6),
        ]
    protocol_intro = (
        "Your Protocol is built from your measured facial analysis and gives you a staged, "
        "non-surgical path toward your own aesthetic potential — never a promise of a specific "
        "outcome, but a practical direction grounded in what your photos and measurements actually "
        "show."
    )
    objective_framing = (
        "This analysis is objective and non-comparative: it highlights your own strengths and the "
        "areas with the most practical opportunity for improvement, rather than measuring you "
        "against a universal ideal."
    )
    half = (len(ANALYSIS_FEATURES) + 1) // 2
    left_features = list(ANALYSIS_FEATURES[:half])
    right_features: list[str | None] = list(ANALYSIS_FEATURES[half:])
    right_features += [None] * (len(left_features) - len(right_features))
    checklist_rows = [
        [
            Paragraph(f"•  {_FEATURE_LABELS[left]}", styles["body"]),
            Paragraph(f"•  {_FEATURE_LABELS[right]}", styles["body"]) if right else "",
        ]
        for left, right in zip(left_features, right_features, strict=True)
    ]
    checklist = Table(checklist_rows, colWidths=[2.85 * inch, 2.85 * inch])
    checklist.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))

    return [
        *_heading1("Your Protocol", styles),
        *photo_flowables,
        Paragraph(protocol_intro, styles["body"]),
        Paragraph(objective_framing, styles["body"]),
        Spacer(1, 6),
        Paragraph("Projected Potential", styles["h2"]),
        checklist,
    ]


_MEASUREMENT_ROW_CAP = 8
"""Phase 14 (Milestone 3, FR-023) -- deepened per-feature metrics can now
run to 8-11 rows for Eyes/Eyebrows, which pushed at least one feature past
a single page (this PDF's own layout requires exactly one page per
feature -- see test_pdf_is_not_duplicated). Capped here, same "condensed
print artifact, full detail lives in the interactive report" posture as
_PROTOCOL_PHASE_ITEM_CAP; never truncates the interactive /report page or
the underlying data, only this table's row count."""


def _measurement_flowables(styles: dict[str, ParagraphStyle], measurement: dict[str, Any]) -> list[Any]:
    """A small Metric/Value table of the actual numeric CV measurements for
    a feature (facial_measurement_service.MeasurementResult.metrics) --
    distinct from "Observations" (the AI's written interpretation of those
    numbers). Hair/Neck (and any feature whose CV extraction failed) have
    no metrics at all (measurement.available is False) -- shown as a short
    note instead of an empty-looking table."""
    metrics = measurement.get("metrics")
    if not measurement.get("available") or not metrics:
        note = measurement.get("note") or "No direct CV measurement for this feature — assessed from your photos."
        return [Paragraph("Measurements", styles["h2"]), Paragraph(note, styles["caption"])]

    items = list(metrics.items())
    rows: list[list[Any]] = [[Paragraph("Metric", styles["table_head"]), Paragraph("Value", styles["table_head"])]]
    for key, value in items[:_MEASUREMENT_ROW_CAP]:
        rows.append(
            [
                Paragraph(_humanize_metric_key(key), styles["table_cell"]),
                Paragraph(f"{value:g}", styles["table_cell"]),
            ]
        )
    table = Table(rows, colWidths=[3.6 * inch, 2.3 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _RECESSED),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, _ACCENT),  # heavier accent rule under the header row only
                ("TOPPADDING", (0, 0), (-1, -1), 3),  # tightened (was 5) -- see _styles()' "h2"/"body" comment
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    flowables: list[Any] = [Paragraph("Measurements", styles["h2"]), table]
    remaining = len(items) - _MEASUREMENT_ROW_CAP
    if remaining > 0:
        flowables.append(Paragraph(f"+ {remaining} more — see the interactive report", styles["caption"]))
    return flowables


_ASSESSMENT_LABELS = {
    "dimorphism": "Dimorphism",
    "prototypicality": "Prototypicality",
    "proportions": "Proportions",
    "symmetry": "Symmetry",
    "face_shape": "Face Shape",
}
_ASSESSMENT_ORDER = ("dimorphism", "prototypicality", "proportions", "symmetry", "face_shape")


def _facial_assessments_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """Milestone 2 (FR-018) -- a compact Category/Score/Label summary table
    for the 5 Facial Assessments, own front-matter page (see
    _FRONT_MATTER_PAGE_COUNT); a bonus page not part of report_template.md
    v3.0's own page list, kept since it's real, tested content the client
    reference simply doesn't happen to show. A category with no data
    (pre-Milestone-2 report, or a photo that
    failed landmark detection) shows "Not yet analyzed" rather than a
    blank/zero row -- report_assembly_service.assemble_sections already
    guarantees all 5 keys are present, so this never KeyErrors."""
    assessments = sections.get("facial_assessments", {})
    rows: list[list[Any]] = [
        [
            Paragraph("Assessment", styles["table_head"]),
            Paragraph("Score", styles["table_head"]),
            Paragraph("Reading", styles["table_head"]),
        ]
    ]
    for category in _ASSESSMENT_ORDER:
        entry = assessments.get(category) or {}
        if entry.get("available"):
            score_text = f"{entry.get('score', 0):.0f}/100"
            label_text = entry.get("label") or ""
        else:
            score_text = "—"
            label_text = "Not yet analyzed"
        rows.append(
            [
                Paragraph(_ASSESSMENT_LABELS[category], styles["table_cell"]),
                Paragraph(score_text, styles["table_cell"]),
                Paragraph(label_text, styles["table_cell"]),
            ]
        )
    table = Table(rows, colWidths=[1.9 * inch, 1.0 * inch, 3.0 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _RECESSED),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, _ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    intro = (
        "Beyond the 11 individual feature areas, these broader measurements describe overall facial "
        "balance and proportion. Like every score in this report, they are first-pass, computer-vision-"
        "derived readings, not a clinical assessment."
    )
    return [
        *_heading1("Facial Assessments", styles),
        Paragraph(intro, styles["body"]),
        Spacer(1, 6),
        table,
    ]


# HarmonyRadarChart.tsx's 6 axes -- same source data
# (sections["harmony_chart"], facial_assessment_service.compute_harmony_chart),
# same axis order/labels, kept in lockstep with the frontend copy rather
# than re-derived.
_HARMONY_AXIS_ORDER = ("harmony", "symmetry", "smoothness", "jawline", "skin", "volume")
_HARMONY_AXIS_LABELS = {
    "harmony": "Harmony",
    "symmetry": "Symmetry",
    "smoothness": "Smoothness",
    "jawline": "Jawline",
    "skin": "Skin",
    "volume": "Volume",
}


class _HarmonyRadarChart(Flowable):
    """Vector-drawn 6-axis radar chart -- the PDF counterpart of the Home
    dashboard's HarmonyRadarChart.tsx (Recharts). Same technique as
    _draw_face_scan_icon/_HairLossScale (drawn directly on the canvas)
    rather than pulling in a charting library for the one chart the PDF
    has. A missing axis value is plotted as 0, matching the web
    component's own `harmonyChart[axis] ?? 0` fallback exactly."""

    _AXIS_COUNT = 6

    def __init__(self, values: dict[str, float | None], diameter: float = 2.3 * inch) -> None:
        super().__init__()
        self.values = values
        self.width = diameter
        self.height = diameter

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return (self.width, self.height)

    def _point(self, axis_index: int, fraction: float) -> tuple[float, float]:
        cx, cy = self.width / 2, self.height / 2
        radius = min(self.width, self.height) / 2 - 16
        angle = math.pi / 2 - axis_index * (2 * math.pi / self._AXIS_COUNT)
        return (cx + radius * fraction * math.cos(angle), cy + radius * fraction * math.sin(angle))

    def draw(self) -> None:
        canv = self.canv
        cx, cy = self.width / 2, self.height / 2
        canv.saveState()

        canv.setStrokeColor(_RECESSED)
        canv.setLineWidth(0.6)
        for ring_fraction in (0.25, 0.5, 0.75, 1.0):
            ring = canv.beginPath()
            for i in range(self._AXIS_COUNT + 1):
                x, y = self._point(i % self._AXIS_COUNT, ring_fraction)
                ring.moveTo(x, y) if i == 0 else ring.lineTo(x, y)
            canv.drawPath(ring, stroke=1, fill=0)
        for i in range(self._AXIS_COUNT):
            x, y = self._point(i, 1.0)
            canv.line(cx, cy, x, y)

        if any(self.values.get(axis) is not None for axis in _HARMONY_AXIS_ORDER):
            data_path = canv.beginPath()
            for i, axis in enumerate(_HARMONY_AXIS_ORDER):
                fraction = max(0.0, min(1.0, (self.values.get(axis) or 0) / 100))
                x, y = self._point(i, fraction)
                data_path.moveTo(x, y) if i == 0 else data_path.lineTo(x, y)
            data_path.close()
            canv.setFillColor(_ACCENT, alpha=0.22)
            canv.setStrokeColor(_ACCENT)
            canv.setLineWidth(1.4)
            canv.drawPath(data_path, stroke=1, fill=1)

        canv.setFillColor(_INK_MUTED)
        canv.setFont("Geist-Regular", 7)
        for i, axis in enumerate(_HARMONY_AXIS_ORDER):
            label_x, label_y = self._point(i, 1.18)
            cos_component = math.cos(math.pi / 2 - i * (2 * math.pi / self._AXIS_COUNT))
            if abs(cos_component) < 0.35:
                canv.drawCentredString(label_x, label_y - 3, _HARMONY_AXIS_LABELS[axis])
            elif cos_component > 0:
                canv.drawString(label_x, label_y - 3, _HARMONY_AXIS_LABELS[axis])
            else:
                canv.drawRightString(label_x, label_y - 3, _HARMONY_AXIS_LABELS[axis])

        canv.restoreState()


def _stat_card(label: str, value: str, styles: dict[str, ParagraphStyle], accent: bool = False) -> Table:
    """One StatRow.tsx card (Overall Score / Evaluated) -- a bordered cell
    with a small uppercase label over a large number, not a table row, so
    it reads the same as the dashboard's own stat cards."""
    value_style = styles["stat_value_accent"] if accent else styles["stat_value"]
    cell = [Paragraph(label.upper(), styles["stat_label"]), Paragraph(value, value_style)]
    card = Table([[cell]], colWidths=[1.72 * inch])
    card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, _RECESSED),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return card


def _stat_row_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """StatRow.tsx's "Overall Score" + "Evaluated ... points" cards --
    same evaluatedPointsCount() logic (available feature scores +
    available facial assessments, out of the fixed 11 + 5), just computed
    in Python from the same underlying `sections` data instead of
    TypeScript from the same API response."""
    feature_scores = sections.get("feature_scores", {})
    facial_assessments = sections.get("facial_assessments", {})
    overall_score = sections.get("overall_score")

    evaluated = sum(1 for v in feature_scores.values() if v.get("available")) + sum(
        1 for v in facial_assessments.values() if v.get("available")
    )
    total = len(feature_scores) + len(facial_assessments)

    cards: list[Any] = []
    if overall_score is not None:
        cards.append(_stat_card("Overall Score", f"{round(overall_score)} / 100", styles))
    if total > 0:
        cards.append(_stat_card("Evaluated", f"{evaluated} / {total} points", styles, accent=True))
    if not cards:
        return []
    row = Table([cards], colWidths=[1.85 * inch] * len(cards))
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return [row, Spacer(1, 10)]


def _score_tone_color(score: float) -> Any:
    """Same 3-band tone PriorityFeaturesList.tsx's scoreTone() uses (amber
    under 50, accent teal at/above 80, plain ink between) -- reused here so
    a priority row's score number carries the same at-a-glance severity
    color on paper as it does on screen."""
    if score < 50:
        return colors.HexColor("#92400E")  # amber-800, same family as the web's text-amber-800
    if score < 80:
        return _INK
    return _ACCENT


_PRIORITY_FEATURE_ROW_CAP = 6


def _priority_features_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """PriorityFeaturesList.tsx, condensed for print: every feature flagged
    "Needs Attention" (the lowest score band), sorted ascending (lowest
    score = most room to improve, shown first). Hair/Neck never appear
    (no CV score exists for either, by design -- same omission the web
    list makes). A thin colored bar under each row is the print
    counterpart of the web list's Progress bar. Capped at
    `_PRIORITY_FEATURE_ROW_CAP` rows for the same reason
    _PROTOCOL_PHASE_ITEM_CAP exists on the Treatment Protocol side (see
    _truncate's docstring) -- at most 9 of the 11 features can ever be
    "Needs Attention" (Hair/Neck are excluded by design), so this is a
    defensive ceiling more than a normally-reached one."""
    feature_scores = sections.get("feature_scores", {})
    ranked = [
        (feature, feature_scores[feature])
        for feature in ANALYSIS_FEATURES
        if (data := feature_scores.get(feature))
        and data.get("available")
        and data.get("score") is not None
        and data.get("label") == "Needs Attention"
    ]
    ranked.sort(key=lambda entry: entry[1]["score"])

    heading = Paragraph("Priority Features to Improve", styles["h2"])
    if not ranked:
        return [heading, Paragraph("No features are flagged as needing attention in this report.", styles["caption"])]

    rows: list[Any] = [heading]
    bar_width = 3.55 * inch
    shown, remainder = ranked[:_PRIORITY_FEATURE_ROW_CAP], ranked[_PRIORITY_FEATURE_ROW_CAP:]
    for feature, data in shown:
        score = data["score"]
        tone = _score_tone_color(score)
        name_row = Table(
            [
                [
                    Paragraph(_FEATURE_LABELS[feature], styles["priority_name"]),
                    Paragraph(f"{round(score)}", styles["priority_name"]),
                ]
            ],
            colWidths=[bar_width - 0.4 * inch, 0.4 * inch],
        )
        name_row.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("TEXTCOLOR", (1, 0), (1, 0), tone),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ]
            )
        )
        rows.append(name_row)
        driver, finding = data.get("driver"), data.get("finding")
        if driver and finding:
            rows.append(Paragraph(f"{driver} — {finding}", styles["priority_finding"]))
        filled = max(0.02, min(1.0, score / 100))
        bar = Table([[""] * 2], colWidths=[bar_width * filled, bar_width * (1 - filled)], rowHeights=[3])
        bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), tone),
                    ("BACKGROUND", (1, 0), (1, 0), _RECESSED),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        rows.append(bar)
        rows.append(Spacer(1, 7))
    if remainder:
        rows.append(Paragraph(f"+ {len(remainder)} more — see each feature's own page", styles["priority_finding"]))
    return rows


# TreatmentProtocolPanel.tsx's PHASES array, kept word-for-word (number,
# title, subtitle, hint) -- the per-report bullet items are what actually
# vary; this structural copy about phase sequencing does not. The
# TreatmentProtocolPanel-only "rationale" sentence per phase is left out
# of the PDF's condensed Overview page (still one paragraph of standing
# copy, not per-report content) to keep this page close to a single
# physical page.
_PROTOCOL_PHASES = (
    ("at_home", "01", "Foundation", "Topicals, hydration, and daily care", "Start here"),
    ("otc_skincare", "02", "Active Care", "Targeted over-the-counter support", "Next"),
    ("in_clinic", "03", "Professional Options", "Discuss with a qualified clinician", "If desired"),
)


_PROTOCOL_PHASE_ITEM_CAP = 3
_PROTOCOL_ITEM_CHAR_CAP = 88


def _truncate(text: str, max_chars: int) -> str:
    """Hard length cap with an ellipsis -- exists solely so the Overview
    page's single-row 2-column Table (_overview_flowables) can never
    exceed one physical page's height, no matter how long a given
    report's AI-generated recommendation sentences happen to be. Unlike
    every other place in this file, this page's content is a *condensed*
    summary by design (report_pdf_service's module docstring), so a
    trimmed sentence here is a deliberate print adaptation, not a lost
    finding -- the full, untruncated sentence already appears verbatim on
    that feature's own page and/or Closing Recommendations. A single-row
    Table's cell content cannot split across pages the way a plain
    top-level flowable stack can, so an unbounded string here is a
    reliable way to crash PDF generation with a ReportLab LayoutError,
    not just a cosmetic overflow -- this cap is a correctness guard, not
    a style choice."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _treatment_protocol_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """TreatmentProtocolPanel.tsx, condensed for print -- same 3 phases,
    one per existing recommendation tier, each phase's real bullet items
    reused verbatim from `sections["recommendations"]`
    (report_assembly_service.classify_recommendations). Unlike the web
    panel (which shows every classified item and can scroll), each phase
    is capped at `_PROTOCOL_PHASE_ITEM_CAP` items here -- the classifier
    routes most closing-recommendation sentences into "at_home" and can
    produce 15-20+ items for one phase, which would blow this condensed
    Overview page well past one page. The remainder isn't lost: every
    feature's own Recommendations already appear on that feature's page,
    and Closing Recommendations repeats the same synthesis in prose."""
    recommendations = sections.get("recommendations") or {}
    heading = Paragraph("Treatment Protocol", styles["h2"])
    has_any = any(recommendations.get(key) for key, *_ in _PROTOCOL_PHASES)
    if not has_any:
        return [heading, Paragraph("No specific protocol recommendations were generated.", styles["caption"])]

    flowables: list[Any] = [heading]
    for key, number, title, subtitle, hint in _PROTOCOL_PHASES:
        items = recommendations.get(key) or []
        if not items:
            continue
        badge = Table(
            [[Paragraph(f"PHASE {number}", ParagraphStyle(
                "PhaseBadge", fontName="Geist-SemiBold", fontSize=7, textColor=colors.white, leading=9,
            ))]],
            colWidths=[0.8 * inch],
        )
        badge.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _ACCENT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ]
            )
        )
        flowables.append(badge)
        flowables.append(Spacer(1, 3))
        flowables.append(Paragraph(f"{title}: {subtitle}", styles["phase_title"]))
        flowables.append(Paragraph(hint, styles["phase_subtitle"]))
        for item in items[:_PROTOCOL_PHASE_ITEM_CAP]:
            flowables.append(
                Paragraph(f"• {_truncate(recommendation_text(item), _PROTOCOL_ITEM_CHAR_CAP)}", styles["phase_bullet"])
            )
        remaining = len(items) - _PROTOCOL_PHASE_ITEM_CAP
        if remaining > 0:
            flowables.append(Paragraph(f"+ {remaining} more — see Closing Recommendations", styles["phase_subtitle"]))
        flowables.append(Spacer(1, 8))
    return flowables


def _overview_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """A new front-matter page (client instruction, 2026-09-15) that
    condenses the Home dashboard (HomeOverviewScreen.tsx) onto one PDF
    page: the stats row (score/points evaluated), Priority Features to
    Improve, the Harmony chart, and the Treatment Protocol -- the same
    2/3-left, 1/3-right column split the web page itself uses, not a new
    layout invented for print."""
    harmony_chart = sections.get("harmony_chart") or {}
    left_col: list[Any] = [
        *_stat_row_flowables(styles, sections),
        *_priority_features_flowables(styles, sections),
        Spacer(1, 8),
        Paragraph("Harmony", styles["h2"]),
        _HarmonyRadarChart(harmony_chart),
    ]
    right_col: list[Any] = _treatment_protocol_flowables(styles, sections)

    table = Table([[left_col, right_col]], colWidths=[4.0 * inch, 2.3 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, 0), 0.5, _RECESSED),
                ("LEFTPADDING", (1, 0), (1, 0), 14),
            ]
        )
    )
    return [*_heading1("Overview", styles), Spacer(1, 4), table]


def _before_after_flowables(
    styles: dict[str, ParagraphStyle], feature: str, image_bytes: bytes | None, visual_bytes: bytes
) -> list[Any]:
    """Milestone 2 (FR-022) -- side-by-side Before/After, only ever called
    once `visual_bytes` (an AI-generated image) actually exists. The
    Before side reuses the same crop `_feature_flowables` would otherwise
    show alone; if no crop exists for this feature (Hair/Neck/Ears are
    best-effort, see facial_measurement_service.extract_feature_crops), a
    short placeholder paragraph stands in rather than crashing the table.
    The disclosure caption is never omitted -- report_design_spec.md
    §9.1's Category-C rule (an AI-generated image is always the most
    visually flagged element on its page, never silently blended in)."""
    max_w, max_h = 2.3 * inch, 1.7 * inch
    before_cell: Any = (
        _framed_image(image_bytes, max_width=max_w, max_height=max_h)
        if image_bytes
        else Paragraph("No original photo available for this feature.", styles["caption"])
    )
    after_cell: Any = _framed_image(visual_bytes, max_width=max_w, max_height=max_h)

    table = Table(
        [
            [Paragraph("Before", styles["table_head"]), Paragraph("After (AI-generated)", styles["table_head"])],
            [before_cell, after_cell],
        ],
        colWidths=[2.5 * inch, 2.5 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, _ACCENT),
            ]
        )
    )
    disclosure = (
        f"The \"After\" image is an AI-generated, illustrative visualization of one suggestion for your "
        f"{_FEATURE_LABELS[feature].lower()} — not a guaranteed outcome, a medical result, or a photograph."
    )
    return [table, Paragraph(disclosure, styles["caption"])]


def _accent_card(cell_content: list[Any], bg_color: Any, width: float) -> Table:
    """Shared visual treatment for every callout box on a feature page (the
    Summary box and the "At a Glance" attributes card): a thin brand-teal
    bar down the left edge plus a tinted fill, rather than a flat tinted
    rectangle alone -- gives each box a deliberate, "designed" edge instead
    of reading as a plain colored background. The bar is always _ACCENT
    (one consistent accent language across the report); `bg_color` is what
    distinguishes one kind of callout from another."""
    bar_width = 4
    table = Table([["", cell_content]], colWidths=[bar_width, width - bar_width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), _ACCENT),
                ("BACKGROUND", (1, 0), (1, -1), bg_color),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("TOPPADDING", (0, 0), (0, -1), 0),
                ("BOTTOMPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 12),
                ("RIGHTPADDING", (1, 0), (1, -1), 12),
                ("TOPPADDING", (1, 0), (1, -1), 7),
                ("BOTTOMPADDING", (1, 0), (1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _summary_callout_flowables(styles: dict[str, ParagraphStyle], feature: str, data: dict[str, Any]) -> list[Any]:
    """New this round -- a direct page-by-page review of the client's own
    reference PDF found every one of its 11 feature pages closes with a
    colored "[Feature] Summary" callout box; this report previously ended
    each feature page with a single bare caption line. Reuses the already-
    computed `summary_callout` text (no new data needed) and folds the
    previous "Confidence: Based on visible indicators" caption into fine
    print inside the same box rather than dropping it."""
    summary_text = data.get("summary_callout") or "No summary available for this feature."
    cell = [
        Paragraph(f"{_FEATURE_LABELS[feature]} Summary", styles["callout_heading"]),
        Paragraph(summary_text, styles["callout_body"]),
        Spacer(1, 4),
        Paragraph("Confidence: Based on visible indicators", styles["caption"]),
    ]
    return [Spacer(1, 4), _accent_card(cell, _CALLOUT_BG, 5.0 * inch)]


# Features whose §9.2 sub-section list includes a second, styling/lifestyle-
# guidance-flavored sub-section beyond the primary one -- Jaw's "Further
# Enhancement" and Skin's "Further Skin Enhancement". Reuses the same
# recommendation_ideas already generated (report_assembly_service.py),
# just named per the spec instead of a generic "Recommendations" heading.
_SECOND_SUBHEADING = {"jaw": "Further Enhancement", "skin": "Further Skin Enhancement"}


class _HairLossScale(Flowable):
    """report_design_spec.md v3.0 §13.3 -- "a horizontal strip of seven
    small illustrated head icons... the icon matching the subject's
    current stage is boxed/highlighted." Drawn directly on the canvas
    (same technique as _draw_face_scan_icon) rather than the previous
    plain-text "Normal 1 [2] 3 4 5 6 7 Extreme" line, which read as
    arbitrary bracket notation rather than an illustration -- an actual
    circle-per-stage strip with the current one filled/ringed is what the
    spec (and a reader) expects "illustrated" to mean here."""

    _STAGE_COUNT = 7
    _RADIUS = 7.5
    _WIDTH = 5.9 * inch

    def __init__(self, current_stage: int) -> None:
        super().__init__()
        self.current_stage = current_stage
        self.width = self._WIDTH
        self.height = 40

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return (self.width, self.height)

    def draw(self) -> None:
        canv = self.canv
        r = self._RADIUS
        usable = self.width - 2 * r
        spacing = usable / (self._STAGE_COUNT - 1)
        cy = self.height - r - 12  # leaves room for the number below and labels below that

        canv.saveState()
        for i in range(self._STAGE_COUNT):
            stage = i + 1
            cx = r + i * spacing
            is_current = stage == self.current_stage
            canv.setFillColor(_HAIR_LOSS_STAGE_FILL if is_current else colors.white)
            canv.setStrokeColor(_ACCENT if is_current else _RECESSED)
            canv.setLineWidth(1.6 if is_current else 0.9)
            canv.circle(cx, cy, r, fill=1, stroke=1)
            canv.setFillColor(_ACCENT if is_current else _INK_MUTED)
            canv.setFont("Geist-Bold" if is_current else "Geist-Regular", 7.5)
            canv.drawCentredString(cx, cy - 2.5, str(stage))

        canv.setFillColor(_INK_MUTED)
        canv.setFont("Geist-Regular", 7.5)
        canv.drawString(0, 0, "Normal")
        canv.drawCentredString(self.width / 2, 0, "Need Attention")
        canv.drawRightString(self.width, 0, "Extreme")
        canv.restoreState()


def _hair_loss_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """report_design_spec.md v3.0 §13.3 / report_template.md §10 -- the
    illustrated stage scale that sits inside the Hair page's own "Hair
    Loss" narrative sub-section (rendered by the sections loop in
    _feature_flowables, which already provides the "Hair Loss" heading
    and its prose -- no second heading here, just the stage caption +
    scale that go right after it). Omitted entirely (not a placeholder
    stage) when the model couldn't assess it from the photos -- never a
    guessed/default stage shown just to fill the section."""
    hair_loss = sections.get("hair_loss")
    if not hair_loss:
        return []
    stage, label = hair_loss.get("stage"), hair_loss.get("label", "")
    return [
        Spacer(1, 3),
        Paragraph(f"Stage {stage} of 7 — {label}", styles["body"]),
        _HairLossScale(stage),
        Spacer(1, 3),
    ]


def _attributes_flowables(styles: dict[str, ParagraphStyle], attributes: dict[str, str]) -> list[Any]:
    """AI-classified named attributes for this feature (e.g. hair's
    hairline/texture/density) -- report_design_spec.md's "match the
    reference's actual content depth" directive.

    Deliberately NOT a second lined Metric/Value-style table directly
    under the real Measurements table above it -- back to back, identically
    styled, the two used to read as one merged table with an odd header
    switch partway down. This is a distinct, tinted "At a Glance" card
    instead (own heading, own background, no cell borders) so a reader can
    tell at a glance that Measurements is raw CV data and this is the AI's
    qualitative read -- two different kinds of finding, not a continuation
    of the same list. Omitted entirely when nothing was confidently
    classified (never a fabricated placeholder row).

    Laid out as a two-column grid rather than one stacked line per
    attribute -- report_design_spec.md v3.0 requires every feature to land
    on exactly one physical page (§9.1: "ten physical pages carry the
    eleven features"), and this card is the single biggest reclaimable
    block of vertical space on a feature page (up to 7 attributes for
    Hair, 6 for Eyes). Halving its row count via two columns is layout
    only -- same labels, same values, nothing summarized or dropped."""
    if not attributes:
        return []
    entries = [
        Paragraph(f"<b>{_humanize_metric_key(key)}</b> — {value}", styles["attribute_line"])
        for key, value in attributes.items()
    ]
    grid_rows: list[list[Any]] = [entries[i : i + 2] for i in range(0, len(entries), 2)]
    if len(grid_rows) and len(grid_rows[-1]) == 1:
        grid_rows[-1].append("")
    col_width = 2.85 * inch
    grid = Table(grid_rows, colWidths=[col_width, col_width])
    grid.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    cell: list[Any] = [Paragraph("At a Glance", styles["callout_heading"]), grid]
    return [Spacer(1, 4), _accent_card(cell, _ATTRIBUTE_BG, 5.9 * inch), Spacer(1, 4)]


def _feature_flowables(
    styles: dict[str, ParagraphStyle],
    feature: str,
    data: dict[str, Any],
    image_bytes: bytes | None,
    visual_bytes: bytes | None = None,
    sections: dict[str, Any] | None = None,
) -> list[Any]:
    flowables: list[Any] = _heading1(_FEATURE_LABELS[feature], styles)
    if visual_bytes:
        flowables.extend(_before_after_flowables(styles, feature, image_bytes, visual_bytes))
    elif image_bytes:
        flowables.append(_framed_image(image_bytes, max_width=2.6 * inch, max_height=1.5 * inch))
        caption = f"Detail from your uploaded photo — {_FEATURE_LABELS[feature].lower()} region."
        flowables.append(Paragraph(caption, styles["caption"]))

    flowables.extend(_measurement_flowables(styles, data.get("measurement") or {}))
    flowables.extend(_attributes_flowables(styles, data.get("attributes") or {}))

    # Named narrative sub-sections (e.g. hair's "Hair Style"/"Hair Loss"/
    # "Hair Health") -- see ai_narrative_service.py's _FEATURE_SUBSECTIONS.
    # Already in canonical heading order from _sanitize_sections; this loop
    # never re-sorts. Hair's illustrated stage scale is interleaved right
    # after its own "Hair Loss" heading's paragraph (matching the reference
    # report's own layout: prose, then the scale, then the next heading),
    # not appended after every section.
    feature_sections = data.get("sections") or {}
    if feature_sections:
        for heading, content in feature_sections.items():
            flowables.append(Paragraph(heading, styles["h2"]))
            flowables.append(Paragraph(content, styles["body"]))
            if feature == "hair" and heading == "Hair Loss":
                flowables.extend(_hair_loss_flowables(styles, sections or {}))
    else:
        flowables.append(Paragraph("Observations", styles["h2"]))
        flowables.append(Paragraph("No observations recorded.", styles["body"]))

    flowables.append(Paragraph("Strengths", styles["h2"]))
    flowables.append(Paragraph(data.get("strengths", "") or "None noted.", styles["body"]))

    flowables.append(Paragraph("Areas of Note", styles["h2"]))
    flowables.append(Paragraph(data.get("areas_of_note", "") or "None notable.", styles["body"]))

    # The Recommendations block + closing Summary callout are kept together
    # as one unit -- previously, when this tail didn't quite fit in the
    # remaining space on a page, ReportLab would leave that leftover space
    # blank and push just the (small) Summary box alone onto an otherwise-
    # empty next page. Grouping them means a too-tight fit moves the whole
    # tail together instead, which reads far better than an orphaned box.
    tail: list[Any] = []
    ideas = data.get("projected_potential") or []
    if ideas:
        tail.append(Paragraph(_SECOND_SUBHEADING.get(feature, "Recommendations"), styles["h2"]))
        tier = data.get("recommendation_tier")
        if tier and tier in _TIER_LABELS:
            tail.append(Paragraph(f"Recommendation tier: {_TIER_LABELS[tier]}", styles["tier_caption"]))
        for idea in ideas:
            tail.append(Paragraph(f"• {recommendation_text(idea)}", styles["body"]))

    tail.extend(_summary_callout_flowables(styles, feature, data))
    flowables.append(KeepTogether(tail))
    return flowables


def _closing_recommendations_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    """report_template.md v3.0 §17 -- a 4-part synthesis (overall harmony/
    structural priorities; periorbital/eye region; hair and lower-face
    grooming; practical next steps + closing disclaimer line), rendered in
    2 columns. `closing_recommendations` is one AI-generated field (the
    same call ai_narrative_service.py always made) -- its prompt now asks
    for this exact 4-paragraph structure (blank-line separated) instead of
    a single generic paragraph; text is split on blank lines and, as a
    defensive fallback for any older stored narrative that predates that
    prompt change and is still one block, on sentence boundaries into
    up to 4 roughly-even parts so this page never renders a single
    unbroken wall of text. No new finding is introduced here -- purely a
    layout of the same synthesis text already produced upstream."""
    text = sections.get("closing_recommendations") or (
        "Your personalized closing recommendations will appear here once your analysis has fully "
        "processed all 11 feature areas."
    )
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
        chunk_size = max(1, -(-len(sentences) // 4))  # ceil division into up to 4 chunks
        paragraphs = [
            ". ".join(sentences[i : i + chunk_size]).rstrip(".") + "."
            for i in range(0, len(sentences), chunk_size)
        ] or [text]

    closing_line = (
        "This protocol is educational, cosmetic guidance only — not a medical diagnosis or a "
        "treatment plan."
    )
    left_col: list[Any] = [Paragraph(p, styles["body"]) for p in paragraphs[0::2]]
    right_col: list[Any] = [Paragraph(p, styles["body"]) for p in paragraphs[1::2]]
    right_col.append(Spacer(1, 6))
    right_col.append(Paragraph(closing_line, styles["caption"]))

    table = Table([[left_col, right_col]], colWidths=[2.85 * inch, 2.85 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, 0), 0.5, _RECESSED),
                ("LEFTPADDING", (1, 0), (1, 0), 14),
            ]
        )
    )
    return [*_heading1("Closing Recommendations", styles), Spacer(1, 8), table]


def _appendix_flowables(styles: dict[str, ParagraphStyle], report: Report) -> list[Any]:
    glossary_rows = [
        [Paragraph("Term", styles["table_head"]), Paragraph("Meaning", styles["table_head"])],
        [
            Paragraph("Measurement", styles["table_cell"]),
            Paragraph("A computer-vision-derived ratio for a feature area, where available.", styles["table_cell"]),
        ],
        [
            Paragraph("Observations", styles["table_cell"]),
            Paragraph("The AI-generated written analysis for a feature area.", styles["table_cell"]),
        ],
        [
            Paragraph("Recommendation", styles["table_cell"]),
            Paragraph("A suggestion worth considering, not a prescription.", styles["table_cell"]),
        ],
    ]
    table = Table(glossary_rows, colWidths=[1.4 * inch, 4.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _RECESSED),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, _ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    methodology = (
        "This report was produced by an automated pipeline: computer-vision landmark measurements "
        "from your uploaded photos were combined with your questionnaire answers and passed to an "
        "AI model, which generated the written analysis above. No part of this report was reviewed "
        "by a human before delivery."
    )
    return [
        *_heading1("Appendix", styles),
        Paragraph("Glossary", styles["h2"]),
        table,
        Spacer(1, 14),
        Paragraph("Methodology", styles["h2"]),
        Paragraph(methodology, styles["body"]),
        Spacer(1, 10),
        Paragraph(
            f"Report generated on {report.created_at.strftime('%B %d, %Y')} · FaceIQ Facial Analysis Report",
            styles["caption"],
        ),
    ]
