"""Branded PDF export (FR-013) -- built with ReportLab, a pure-Python
dependency with no system-level requirements (chosen over WeasyPrint/
Playwright specifically for portable, dependency-free installs across dev
machines -- see D:\\zzz\\report-generation\\plans.md). Renders a Report's
already-assembled `sections` JSON plus its per-feature cropped images
(see facial_measurement_service.extract_feature_crops); does not re-derive
or re-fetch anything else.

Page structure (cover, disclaimer, "Understanding Your Report", an Overview
table, one page per feature, consolidated Recommendations + Next Steps, and
an Appendix) was adopted from a client-provided reference report. Colors
and the FaceIQ wordmark now match the actual app theme (frontend/src/app/
globals.css's `:root` tokens, converted from OKLCH to sRGB hex once below)
and the app's own two-weight wordmark styling (Logo.tsx: "Face" semibold +
"IQ" black) rather than the reference's own palette/branding.
"""

import io
from typing import Any

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image as RLImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.report import Report
from app.models.user import User
from app.services.facial_measurement_service import ANALYSIS_FEATURES

# App theme tokens (frontend/src/app/globals.css `:root`), converted from
# OKLCH to sRGB hex -- keeps the PDF visually consistent with the web app
# rather than an independent palette.
_PAPER = colors.HexColor("#F1F4F6")  # matches (protected)/layout.tsx's page-shell background
_INK = colors.HexColor("#14191A")  # --foreground
_INK_MUTED = colors.HexColor("#5A6668")  # --muted-foreground
_ACCENT = colors.HexColor("#4E7A82")  # --primary
_RECESSED = colors.HexColor("#D7E0E2")  # --border

_PAGE_SIZE = LETTER
_MARGIN = 0.85 * inch
_CONFIDENTIALITY_NOTE = "Personal and confidential — generated for your individual use."
# Cover, About, Understanding, Overview -- always exactly one page each
# (fixed-length static copy + an 11-row table that comfortably fits one
# Letter page), so front-matter page count is a safe compile-time constant
# rather than something computed at render time.
_FRONT_MATTER_PAGE_COUNT = 4


def _to_roman(num: int) -> str:
    values = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    result: list[str] = []
    for value, symbol in values:
        while num >= value:
            result.append(symbol)
            num -= value
    return "".join(result)


def _draw_wordmark(canvas: Canvas, x: float, y: float, size: float, center: bool = False) -> None:
    """Renders "FaceIQ" matching Logo.tsx: "Face" semibold + "IQ" black.
    ReportLab's base-14 fonts have no true black/900 weight, so "IQ" is
    faux-bolded with a tiny double-strike offset -- a standard technique
    for approximating a heavier weight without embedding a custom font."""
    canvas.saveState()
    canvas.setFillColor(_INK)
    face_font, iq_font = "Helvetica-Bold", "Helvetica-Bold"
    face_width = canvas.stringWidth("Face", face_font, size)
    iq_width = canvas.stringWidth("IQ", iq_font, size)
    total_width = face_width + iq_width
    start_x = x - total_width / 2 if center else x

    canvas.setFont(face_font, size)
    canvas.drawString(start_x, y, "Face")
    canvas.setFont(iq_font, size)
    iq_x = start_x + face_width
    canvas.drawString(iq_x, y, "IQ")
    canvas.drawString(iq_x + 0.3, y, "IQ")  # faux-bold double-strike
    canvas.restoreState()


def _draw_face_scan_icon(canvas: Canvas, center_x: float, center_y: float, size: float) -> None:
    """A simple vector face-scan glyph (viewfinder corners + a minimal
    face) in the brand accent color -- drawn with plain shapes since no
    external image asset exists for this, per the report's "facial
    analysis" framing."""
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

    canvas.setStrokeColor(_INK)
    canvas.setLineWidth(1.3)
    face_r = size * 0.28
    canvas.circle(center_x, center_y, face_r, stroke=1, fill=0)
    eye_offset_x, eye_offset_y = face_r * 0.42, face_r * 0.25
    eye_r = face_r * 0.09
    canvas.setFillColor(_INK)
    canvas.circle(center_x - eye_offset_x, center_y + eye_offset_y, eye_r, stroke=0, fill=1)
    canvas.circle(center_x + eye_offset_x, center_y + eye_offset_y, eye_r, stroke=0, fill=1)
    smile_path = canvas.beginPath()
    smile_path.arc(
        center_x - face_r * 0.45,
        center_y - face_r * 0.65,
        center_x + face_r * 0.45,
        center_y + face_r * 0.05,
        startAng=200,
        extent=140,
    )
    canvas.drawPath(smile_path, stroke=1, fill=0)
    canvas.restoreState()

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


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"], textColor=_INK, fontSize=26, leading=30, alignment=TA_CENTER
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=base["Normal"], textColor=_ACCENT, fontSize=13, alignment=TA_CENTER, spaceBefore=6
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta", parent=base["Normal"], textColor=_INK_MUTED, fontSize=9, alignment=TA_CENTER, spaceBefore=18
        ),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], textColor=_INK, fontSize=19, spaceAfter=10),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], textColor=_INK, fontSize=13, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["BodyText"], textColor=_INK, fontSize=10, leading=14, spaceAfter=8),
        "muted": ParagraphStyle("Muted", parent=base["BodyText"], textColor=_INK_MUTED, fontSize=8.5, leading=12),
        "caption": ParagraphStyle(
            "Caption", parent=base["BodyText"], textColor=_INK_MUTED, fontSize=8, leading=11, spaceAfter=6
        ),
        "table_cell": ParagraphStyle("TableCell", parent=base["BodyText"], textColor=_INK, fontSize=9, leading=12),
        "table_head": ParagraphStyle("TableHead", parent=base["BodyText"], textColor=_ACCENT, fontSize=9.5, leading=12),
    }


def _scaled_image(image_bytes: bytes, max_width: float, max_height: float) -> RLImage:
    with PILImage.open(io.BytesIO(image_bytes)) as im:
        w, h = im.size
    scale = min(max_width / w, max_height / h, 1.0)
    return RLImage(io.BytesIO(image_bytes), width=w * scale, height=h * scale)


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

    def _draw_footer(self, page_number: int) -> None:
        width, _ = _PAGE_SIZE
        if page_number <= _FRONT_MATTER_PAGE_COUNT:
            label = _to_roman(page_number)
        else:
            label = str(page_number - _FRONT_MATTER_PAGE_COUNT)
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(_INK_MUTED)
        self.drawRightString(width - _MARGIN, 0.55 * inch, label)
        self.restoreState()


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
    canvas.setFont("Helvetica", 9)
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


def render_pdf(report: Report, user: User, images: dict[str, bytes] | None = None) -> bytes:
    images = images or {}
    sections = report.sections
    styles = _styles()
    generated_label = f"Generated {report.created_at.strftime('%B %d, %Y')}"

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
    story.extend(_about_flowables(styles, sections))
    story.append(PageBreak())
    story.extend(_understanding_flowables(styles, sections))
    story.append(PageBreak())
    story.extend(_overview_flowables(styles, sections))
    story.append(PageBreak())

    features = sections.get("features", {})
    for index, feature in enumerate(ANALYSIS_FEATURES):
        story.extend(_feature_flowables(styles, feature, features.get(feature, {}), images.get(feature)))
        if index < len(ANALYSIS_FEATURES) - 1:
            story.append(PageBreak())
    story.append(PageBreak())

    story.extend(_recommendations_flowables(styles, features))
    story.append(PageBreak())
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
    ]


def _about_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    return [
        Paragraph("About This Report", styles["h1"]),
        Paragraph(sections.get("intro", ""), styles["body"]),
        Spacer(1, 10),
        Paragraph(_CONFIDENTIALITY_NOTE, styles["caption"]),
    ]


def _understanding_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    return [
        Paragraph("Understanding Your Report", styles["h1"]),
        Paragraph(sections.get("understanding_your_results", ""), styles["body"]),
    ]


def _overview_flowables(styles: dict[str, ParagraphStyle], sections: dict[str, Any]) -> list[Any]:
    features = sections.get("features", {})
    rows: list[list[Any]] = [
        [Paragraph("Feature Area", styles["table_head"]), Paragraph("At a Glance", styles["table_head"])]
    ]
    for feature in ANALYSIS_FEATURES:
        data = features.get(feature, {})
        rows.append(
            [
                Paragraph(_FEATURE_LABELS[feature], styles["table_cell"]),
                Paragraph(data.get("summary_callout", ""), styles["table_cell"]),
            ]
        )
    table = Table(rows, colWidths=[1.3 * inch, 4.6 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _RECESSED),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    overview_intro = "A quick index of every feature area covered in this report, in the order they appear below."
    return [
        Paragraph("Overview", styles["h1"]),
        Paragraph(overview_intro, styles["body"]),
        Spacer(1, 6),
        table,
    ]


def _feature_flowables(
    styles: dict[str, ParagraphStyle], feature: str, data: dict[str, Any], image_bytes: bytes | None
) -> list[Any]:
    flowables: list[Any] = [Paragraph(_FEATURE_LABELS[feature], styles["h1"])]
    if image_bytes:
        flowables.append(_scaled_image(image_bytes, max_width=2.6 * inch, max_height=1.9 * inch))
        caption = f"Detail from your uploaded photo — {_FEATURE_LABELS[feature].lower()} region."
        flowables.append(Paragraph(caption, styles["caption"]))

    flowables.append(Paragraph("Observations", styles["h2"]))
    flowables.append(Paragraph(data.get("narrative", "") or "No observations recorded.", styles["body"]))

    flowables.append(Paragraph("Strengths", styles["h2"]))
    flowables.append(Paragraph(data.get("strengths", "") or "None noted.", styles["body"]))

    flowables.append(Paragraph("Areas of Note", styles["h2"]))
    flowables.append(Paragraph(data.get("areas_of_note", "") or "None notable.", styles["body"]))

    ideas = data.get("projected_potential") or []
    if ideas:
        flowables.append(Paragraph("Recommendations", styles["h2"]))
        for idea in ideas:
            flowables.append(Paragraph(f"• {idea}", styles["body"]))

    flowables.append(Paragraph("Confidence: Based on visible indicators", styles["caption"]))
    return flowables


def _recommendations_flowables(styles: dict[str, ParagraphStyle], features: dict[str, Any]) -> list[Any]:
    per_feature: list[tuple[str, str]] = []
    for feature in ANALYSIS_FEATURES:
        ideas = features.get(feature, {}).get("projected_potential") or []
        if ideas:
            per_feature.append((_FEATURE_LABELS[feature], " ".join(ideas)))

    flowables: list[Any] = [Paragraph("Recommendations", styles["h1"])]
    for label, text in per_feature:
        flowables.append(Paragraph(f"<b>{label}:</b> {text}", styles["body"]))

    flowables.append(Paragraph("Next Steps", styles["h2"]))
    for index, (label, text) in enumerate(per_feature, start=1):
        flowables.append(Paragraph(f"{index}. ({label}) {text}", styles["body"]))
    return flowables


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
        Paragraph("Appendix", styles["h1"]),
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
