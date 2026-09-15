# Report Design Spec
### AI Facial Analysis Platform — Enriched Report Design Specification (Milestone 2)
### Visual system: reference-exact (Meridian retired)

**Status:** ACTIVE — version 3.0 (2026-09-15). This version fully replaces the "Meridian" design system (v1–v2, see `report_design_spec.md`'s own prior revisions) and closes out both of that system's Reconciliation Notes.

**Legend:** ✅ Confirmed (directly observed in the reference) · 🔵 Proposed (a reasonable default where the reference is a static PDF/screenshot and cannot show a mechanic — loading, error, locked states) · 🔴 TBD (a genuine open decision the reference cannot resolve)

---

## 0. What Changed, and Why (Read This First)

**Directive (2026-09-15, Nishant):** The client-supplied reference report — `MyFace-Protocol-test-1 (3).pdf`, already reviewed in [`claude/PHASE2_REQUIREMENTS_ANALYSIS.md`](./claude/PHASE2_REQUIREMENTS_ANALYSIS.md) §2.1 and §2.7 — is now the **binding visual and structural target** for the Phase 2 report. Reproduce its format and content exactly, not merely draw inspiration from it. This is a deliberate, one-time override of `principles-and-workflow.md`'s general posture that "reference material informs but does not confirm" — that general posture still governs every other artifact in this project; it has been explicitly superseded **for this one artifact, by this one dated instruction.**

**What this retires:**
- The abstract, token-based "Meridian" visual system (§1 of the prior version) — its color/type/icon tokens, its "three reading passes" navigation framing, and its cover-only-restraint treatment are all retired. The reference report has real, observable colors, layout, and page structure; this document now specifies those directly instead of an invented abstract system.
- The "seven-pose Multi-Pose Evidence Overview" vs. "3-angle Multi-Angle Evidence Overview" debate carried across the two Reconciliation Notes. This document does not reopen or resolve that question — see §17. The reference report's photography does not by itself prove a capture-angle count (its many crops, profiles, and split-face composites could be sourced from more angles than three, or reused across sessions), so it is out of scope here and remains `photo_capture_spec.md` (`ASM-005`)'s call.
- The single six-axis "Harmony Chart" as the *only* chart. The reference report has **two distinct radar charts** on two different pages — see §12.

**What carries forward unchanged:** the eleven-feature set (`client_requirements.md` `FR-009`/`BR-008`, `BR-011` — Smile folds into Lips, not a 12th feature); the non-clinical/cosmetic recommendation boundary; the general accessibility baseline (§18); the print-first/PDF-and-web-both design goal.

**What's new here, not in any prior version of this document:** the Report Dashboard as a fully-specified page in its own right (§4), a "Priority features to improve" table, a "Feature Evaluation" table, a phased "Treatment Protocol" card, a "Facial Age" component, a second (11-axis, two-series) radar chart, an illustrated Hair Loss scale, and a much broader photographic evidence model (profile shots, tight crops, annotated/measurement overlays, a split-face composite) than the old "3-angle gallery" described.

---

## 1. Authority

| Document | Relationship |
|---|---|
| `client_requirements.md` | Project source of truth; unaffected by this document |
| `claude/PHASE2_REQUIREMENTS_ANALYSIS.md` §2.1, §2.7, §3 (row 8), §6 (OI-2) | Prior review of the same reference PDF; this document operationalizes that review into an implementable design spec and does not contradict it |
| `milestone2_phase_plan.md` / `claude/PHASE2_PHASE_WISE_REQUIREMENTS.md` | Implementation sequencing; Phase 12 ("Meridian Design Implementation") should be read against this document, not the retired Meridian spec |
| `database-design.md`, `api-specification.md` | Exact field mapping and payment-gating contract; this document does not redefine either — see §16 |
| `report_template.md` | Companion document — content/copy rules for every page/section defined here |
| `photo_capture_spec.md` (`ASM-005`) | Governs the actual capture-angle count; not reopened by this document (§17) |

**This document does not:** modify application code, define scoring formulas, define database/API fields, or resolve the capture-angle question. It produces one artifact: `report_design_spec.md` (this file).

---

## 2. Two Report Surfaces

The reference material shows the report exists in two forms, sharing content but not layout:

| Surface | What it is | Covered in |
|---|---|---|
| **Report Dashboard** (web) | An interactive "Protocol Summary" screen — the first thing a user sees, richer and more data-dense than a PDF cover | §4 |
| **Generated PDF** (16 pages) | The exportable/printable report: disclaimer, introduction, protocol overview, eleven feature pages, closing recommendations | §5–§10 |

Both surfaces present the *same* underlying analysis; the Dashboard is not a subset or a teaser — it has its own components (Priority features table, Treatment Protocol, Facial Age, Feature Evaluation table) that do not appear anywhere in the PDF, and the PDF has its own components (Disclaimer/Privacy page, page-by-page Before/After pairs, closing synthesis) that do not appear on the Dashboard. Neither is a re-layout of the other.

---

## 3. Design Tokens

🔴 **All hex values below are visually approximated from the reference PDF/screenshot, not sampled from brand assets** — no client branding assets exist for this project (`client_requirements.md` `CON-003`), so exact values are an implementation decision, not a reference fact. Treat every value in this section as a starting point for design review, not a locked deliverable.

### 3.1 Color

| Role | Approx. value | Usage observed in reference |
|---|---|---|
| `ink.heading` | `#1A2230` (near-black navy/charcoal) | Page titles ("Hair", "Disclaimer", "MYFACE" wordmark), body headings |
| `ink.subheading` | `#9FB4C7` (muted slate blue) | The second word of every two-line page title ("Recommendations", "the Results", "Policy") — always lighter/lower-contrast than the first line |
| `ink.body` | `#2A2D31` | Running paragraph text |
| `ink.muted` | `#6B7280` | Captions, footnotes, table sub-rows, page numbers |
| `accent.primary` (teal-green) | `#2E8B7D` | Overall score numeral, top-of-page accent bar on every PDF page, chart line/fill, "PROTOCOL" phase-number label |
| `surface.page` | `#FFFFFF` (PDF) / `#F5F6F7` (Dashboard background) | Page background |
| `surface.card` | `#FFFFFF` with a thin `#E5E7EB` border | Every card/tile/table container |
| `surface.summaryBox` | `#DCEEE8` (light sage/mint) | Every per-feature "Summary" callout box |
| `surface.badgeChip` | `#33343680` (dark, semi-opaque) with white text | Corner label chips on photos (BEFORE / AFTER / PROFILE / ANALYSIS / LIPS / EYES) |

### 3.2 Typography

| Token | Observed usage |
|---|---|
| `type.display` | Large two-line page titles (bold heading line + lighter subheading line), cover/dashboard numerals |
| `type.heading` | Sub-section headings within a page ("Hair Style", "Hair Loss", "Nose Summary") |
| `type.body` | Running paragraph copy |
| `type.numeral` | Scores, table figures, page numbers — tabular alignment |

Exact typeface families are 🔴 an implementation choice; what's fixed is the role system itself (display / heading / body / numeral).

### 3.3 Shape & Spacing

One corner radius applied to every card, image tile, and badge chip (moderate rounded-rectangle, observed consistently across dashboard cards, PDF photo frames, and the Priority/Feature Evaluation table rows). One consistent vertical spacing scale between stacked components. A thin teal-green rule runs across the very top of every PDF page (the only full-bleed color element on an otherwise white page) and repeats as a horizontal divider under every page title.

### 3.4 Badge / Label Chips

A small dark, semi-opaque rounded-rectangle chip, white all-caps text, fixed to the top-left corner of a photo. This is the **only** evidence-labeling mechanism observed — there is no separate icon system, no colored border-by-category, no second chip style. Observed chip labels: `BEFORE`, `AFTER`, `POTENTIAL`, `PROFILE`, `ANALYSIS`, `LIPS`, `EYES`. See §11 for the full pattern.

---

## 4. Report Dashboard ("Protocol Summary")

✅ Confirmed structure, directly observed. This is the web-native landing view of a completed analysis — richer than any PDF page and not reproduced by any single PDF page.

### 4.1 Top Bar
`PROTOCOL | {subject name} #{reference number} {date}` on the left; the `MyFace`-equivalent product wordmark on the right.

### 4.2 Three Stat Tiles (full-width row, top)
| Tile | Content |
|---|---|
| Overall Score | Large numeral in `accent.primary` + `/100` |
| Evaluated | A point count (e.g. "170+") + `points` |
| Analysis Time | A duration (e.g. "1 day") |

### 4.3 Left Column
1. **Identity card** — grey-filled tile: subject's display name (large), `PROTOCOL #{reference}`, `Assessed {date}`, `Overall {score}/100`.
2. **"Your Facial Analysis" card** — a short explanatory paragraph, three numbered steps (1. Measured morphology, 2. Projected potential — "Before / After visualisation", 3. Staged protocol — "Non-surgical phase guidance"), paired with a labeled face diagram (forehead/eyes/nose/mouth region call-outs on a face silhouette) and a restated three-up summary row (Score / Evaluated / Analysis Time, mirroring §4.2).
3. **Priority features to improve** — a table surfacing the *lowest-scoring* features only (not all eleven), each row showing: feature name, score `/100`, a short qualitative label (e.g. "Needs attention", "Balanced"), and 1–3 attribute sub-rows (e.g. under Skin: "Evenness — Noticeably uneven", "Texture — Textured"). See §13.1.

### 4.4 Middle Column
1. **Before / Potential photo pair** — two frontal photos side by side, badge-chipped `BEFORE` and `POTENTIAL`.
2. **Facial Age card** — a single numeral (e.g. "28") plus a horizontal range slider (labeled endpoints, e.g. "5" and "65") with a single pointer marking the estimated age. Not a range or a projection — one current estimate. 🔵 No interaction behavior is observable from a static reference; treat the slider as a read-only visualization, not an input control, unless product decides otherwise (🔴).
3. **Harmony Profile** — a 6-axis radar chart. See §12.1.
4. **Overview** — a short paragraph synthesizing the overall harmony finding in prose (e.g. "This evidence-based non-surgical protocol is grounded in the subject's measured facial analysis (overall harmony described as *{qualitative label}*), organised around key aesthetic features.").

### 4.5 Right Column
**Treatment Protocol card** — see §14.

### 4.6 Bottom, Full-Width
**Feature Evaluation table** — Zone / Finding / Reference columns. See §13.2.

### 4.7 Footer
A single restated evaluation-point count (e.g. "170+ evaluation points").

---

## 5. PDF Page 02 — Disclaimer & Privacy Policy

✅ Confirmed. Two-column layout under the standard PDF page header. Numbered `02` in the reference's own printed folio — the Dashboard (§4) is the unnumbered page that precedes it when the Dashboard is exported alongside the PDF; a PDF generated standalone begins its own numbering at this page (still labeled `02`, matching the reference exactly, rather than renumbered to `01`).

| Column | Content |
|---|---|
| Left — **Disclaimer Policy** | Informational/educational purpose only; not medical/clinical/professional advice; no warranty of accuracy; a bolded closing paragraph restating that any treatment decision belongs to a qualified professional |
| Right — **Privacy Policy** | What the report is used for; that supplied content (images/video) is stored for a bounded retention window (observed: "up to 1 year for reference purposes"); that modified client images are stored as a whole within the report; a cookie/analytics note; a link to the full privacy policy |
| Footer (left, below the rule) | `{Brand} Inc` — "The following report was commissioned for {subject} on {month/year}." |

This page's copy is legally-reviewed standing text — see `report_template.md` §5.2 for the content rules; this section governs layout only (two equal columns, a vertical rule between them, no imagery).

---

## 6. PDF Page 03 — Introduction

✅ Confirmed. Two-column layout.

| Column | Content |
|---|---|
| Left, top | Short intro paragraph (cephalometric/measurement-based framing, "less subjective" positioning) |
| Left, bottom (below a horizontal rule) | **Limitations** — a short paragraph on what can affect measurement accuracy (head position, lighting, camera quality, absence of radiographic imaging) and a restated "not a medical diagnosis" line |
| Right | **Contents** — a simple two-column-free list: section name + page number, one row per page from "Understanding the Results" through "Closing Recommendations" |

---

## 7. PDF Page 04 — Understanding the Results

✅ Confirmed. Four large numbered principles (`01`–`04`), stacked vertically, each a bold one-line headline + a one-to-two-sentence explanation. Observed headlines:

1. These recommendations focus on key markers of facial health and harmony (not "what makes the subject unique").
2. **{Brand} does not rate attractiveness** — assessment highlights what works for the subject's own features via objective measurement, not a universal standard.
3. The protocol mixes foundational and advanced recommendations (fundamentals like SPF/sleep/hydration support the effectiveness of more targeted guidance).
4. All recommendations are informational/aesthetic only — any in-clinic treatment or prescription should be discussed with a qualified medical professional.

Principle 2 is the direct, explicit "does not rate attractiveness" framing this project's requirements already require (`client_requirements.md` FR-004/FR-012) — it should be reproduced as its own numbered principle, not folded into general disclaimer language.

---

## 8. PDF Page 05 — "{Subject}'s Protocol"

✅ Confirmed. This is the PDF's overview/summary page — distinct from both the Dashboard (§4) and the per-feature pages (§9).

| Region | Content |
|---|---|
| Top, full-width | A large **Before / After** photo pair (frontal, badge-chipped), the largest images in the document |
| Below-left | Two short paragraphs: what the protocol is for, and a framing statement that the analysis is objective/non-comparative ("highlights strengths and areas for improvement" rather than measuring against a universal ideal) |
| Below-left, "Projected potential" | A heading + the fixed list of all eleven features, in two columns (not the per-feature detail — just the list, establishing what's covered ahead) |
| Below-right | The **second radar chart** — 11 axes (one per feature), two overlaid series with a legend: "Projected Potential" and "Client Values". See §12.2. |

---

## 9. PDF Pages 06–15 — The Eleven Feature Pages

✅ Confirmed. Ten physical pages carry the eleven features (Eyebrows and Eyes share one page — see §9.2). Fixed order: **Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears** (`BR-008`/`BR-011`, unchanged).

### 9.1 Shared Page Anatomy

Every feature page carries the standard PDF header/footer (brand wordmark, `PAGE / NN`, top accent rule) and a two-line page title in the pattern `{Feature}` / `Recommendations` (bold heading + muted subheading, per §3.2). Below that, the content is **not** a rigid fixed grid — page layout varies per feature (see §9.2) — but every page shares these recurring building blocks:

- One or more **photo panels**, each badge-chipped per §3.4/§11.
- A **Before/After photo pair**, badge-chipped, specific to that feature (not a reused dashboard image).
- One or more **prose sub-sections**, each with its own bold sub-heading (e.g. "Hair Style", "Nose", "Jaw Structure").
- A **Summary callout box** (`surface.summaryBox`) — always titled `"{Feature} Summary"` or `"{Feature} Region Summary"`, containing a 2–4 sentence synthesis. Position varies: a right-column card on some pages (Hair, Eye, Nose, Chin\*, Skin), a full-width band on others (Cheek, Jaw, Lip, Chin\*, Ear, Neck) — 🔵 treat as a responsive variant of one component, not two components.
- Occasionally, an italic **"Recommendation tier: {tier}"** caption directly under a sub-section's body text (observed only on the Hair page, both under "Hair Style" and "Hair Health"). 🔴 Open whether this is meant to appear per-section across all eleven features (and simply wasn't populated for the other ten in this sample) or is specific to sections with a clear OTC/non-invasive recommendation. Recommend implementing it as a general, optional per-sub-section field (present when a recommendation tier applies, absent otherwise) rather than a Hair-only special case — see `report_template.md` §11.4.

### 9.2 Per-Feature Breakdown

| Feature (page) | Sub-sections | Photo panels | Notable unique element |
|---|---|---|---|
| **Hair** (p.6) | Hair Style; Hair Loss; Hair Health | Before/After (hairline close-up, top-down angle) | The **Hair Loss scale** — an illustrated 7-stage strip, Normal → Need Attention → Extreme, current stage boxed/highlighted. See §13.3. |
| **Eyebrows + Eyes** (p.7) | Eyebrows; Eyelashes; Eyes; Under eye | Before/After (brow close-up); a small cropped `EYES` panel (isolated eye-shape close-ups on a neutral tile, no face context) | Two features share one page — the only page that does |
| **Nose** (p.8) | Nose | `PROFILE` panel (side view); Before/After (tight nostril/tip crop) | Profile (side-angle) photo, not frontal |
| **Cheeks** (p.9) | Cheek Structure | `ANALYSIS` panel — a frontal photo with white line-overlay annotations (measurement triangulation across cheekbones/jaw); Before/After | The only page with visible measurement-line overlay annotation |
| **Jaw** (p.10) | Jaw Structure; Further Enhancement | `PROFILE` panel (side view); Before/After (lower-face crop) | Two-part prose (structure + styling/enhancement guidance) |
| **Lips** (p.11) | Lips | `LIPS` panel — isolated lip crop on a neutral tile; Before/After | Summary box is full-width, not right-column |
| **Chin** (p.12) | Chin | Two `PROFILE` panels (side view, each with a thin dashed vertical reference line overlay); Before/After (chin/jawline crop) | Only page with two profile shots of the same type |
| **Skin** (p.13) | Skincare Protocol; Further Skin Enhancement | A large split-face composite (left/right halves of one frontal photo divided by a dashed vertical line, for texture/tone comparison); Before/After (cheek-skin crop) | Split-face composite is unique to Skin |
| **Neck** (p.14) | Neck Size; Neck Skin | Before/After (neck/jawline-from-below crop) | No profile or annotated panel — Before/After only |
| **Ears** (p.15) | Ear Structure | Before/After (frontal, ear-focused crop) | No dedicated ear close-up beyond the Before/After pair |

Every page's prose references the subject's questionnaire history where relevant (e.g. Jaw and Ear pages both note "because medical conditions are reported, [conservative approach]") — a content rule, not a layout rule; see `report_template.md` §14.

---

## 10. PDF Page 16 — Closing Recommendations

✅ Confirmed. Two-column prose, no images, no summary box, no new photo evidence. Four paragraphs synthesizing across all eleven features (see `report_template.md` §17 for the exact synthesis rules) plus a closing line restating that the protocol is educational guidance, not medical diagnosis or treatment.

---

## 11. Evidence / Photo Treatment

✅ Confirmed pattern, observed on every photographed page:

- **One labeling mechanism**: a small dark chip, white all-caps text, top-left corner of the photo. No second badge style, no color-coded category system, no icon-plus-label combination — just the chip.
- **Chip vocabulary observed**: `BEFORE`, `AFTER`, `POTENTIAL` (Dashboard only — the PDF uses `AFTER`, not `POTENTIAL`, for the same pairing), `PROFILE`, `ANALYSIS`, `LIPS`, `EYES`. New chip labels should follow the same pattern: a single all-caps word naming what the photo *is*, not a category taxonomy.
- **No AI-generation disclosure language is visible anywhere in the reference** — no "simulated," "illustrative," or similar caption accompanies any Before/After or Potential image. This is a **gap, not a confirmed absence** relative to this project's own standing rule (`report_template.md` §16.4 / `client_requirements.md`) that AI-generated visualizations must be clearly labeled as such — the reference cannot be read as license to drop that disclosure. Where this project's Before/After images are AI-generated (`FR-022`), the disclosure requirement stands even though the visual reference doesn't show one. 🔴 flagged for explicit confirmation, not silently resolved either way.
- **Annotation overlays** (Cheek's measurement lines, Chin's dashed reference line, Skin's split-face divider) use a thin white or dashed line directly on the photo — no separate legend, no colored zones.
- Photos are real color photography throughout — no monochrome/desaturated treatment, no illustration style except the Hair Loss scale icons (§13.3) and the labeled face diagram on the Dashboard (§4.3).

---

## 12. Charts

The reference contains **two distinct radar/spider charts.** They are not the same component at two sizes — they plot different axis sets and different data.

### 12.1 Harmony Profile (Dashboard only)

- **6 axes**, abbreviated labels observed: Har(mony), Sym(metry), Smo(othness), Jaw, Skin, Vol(ume).
- **One series** (single teal-green outline/fill).
- No numeric value labels at vertices in the observed render — 🔵 recommend adding them (consistent with this project's general non-color-only-signaling accessibility rule, §18) even though the reference omits them.
- Appears only on the Dashboard, not in the PDF.

### 12.2 Projected Potential vs. Client Values (PDF "Protocol" page only)

- **11 axes**, one per feature, full names (Hair, Brows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears).
- **Two series**, overlaid, with a legend: "Projected Potential" (lighter/teal fill) and "Client Values" (darker outline).
- Appears only on the PDF's overview page, not on the Dashboard.

### 12.3 Governing Rule (carried forward, unchanged in substance from the retired Meridian spec)

Both charts remain a pure presentation layer over authoritative scoring data. Neither chart computes, estimates, or fills in a missing value; a `null`/non-scorable axis is never plotted as `0`. This rule is not weakened by adopting the reference's exact visual treatment.

---

## 13. Tables

### 13.1 Priority Features to Improve (Dashboard)

Rows: feature name, score `/100`, short qualitative label, 1–3 attribute sub-rows (attribute name + plain-language value). Shows only the *lowest-scoring* subset of the eleven features, not all eleven — 🔴 exact selection cutoff (bottom N, or below a score threshold) is not evidenced by the reference; a scoring-layer decision, not a design one.

### 13.2 Feature Evaluation (Dashboard, bottom, full-width)

Columns: **Zone**, **Finding**, **Reference**. Rows observed: Forehead, Eyes, Nose, Lips, Jawline — a shorter, differently-grouped list than the eleven-feature set (e.g. "Jawline" and "Forehead" rather than "Jaw" and "Hair"). 🔴 Whether this table's "Zone" list is a fixed different taxonomy from the eleven report features, or a configurable subset, is not resolved by the reference and should be confirmed against the scoring layer's actual zone/measurement vocabulary before implementation.

### 13.3 Hair Loss Scale (Hair page only)

A horizontal strip of seven small illustrated head icons, left-to-right, labeled at three points along the strip: "Normal" (left), "Need Attention" (center), "Extreme" (right). The icon matching the subject's current stage is boxed/highlighted (a colored border). This is the only illustrated (non-photographic, non-chart) component in the entire report.

---

## 14. Treatment Protocol Card (Dashboard, right column)

✅ Confirmed. A single visible phase card (the reference shows Phase 01 only — whether additional phases exist and are scrollable/paginated is not observable from a static reference, 🔴):

- `PHASE 01` label in `accent.primary`
- Phase title (e.g. "Foundation & Photoprotection")
- A duration/timing line (e.g. "Immediate–Weeks 1-12")
- A short bullet list of the specific driving findings (e.g. "Skin–Evenness: Noticeably uneven")
- A closing paragraph synthesizing why this phase comes first, in prose

🔴 Whether later phases (Phase 02, 03…) exist in the full product and are simply not visible in this sample, or whether this build only produces one phase, is not evidenced by the reference and should be confirmed against `PHASE2_REQUIREMENTS_ANALYSIS.md` §2.1 (which documents a live-app sample showing three phases) before scoping implementation — see §20 item 3.

---

## 15. Facial Age Component (Dashboard)

A numeral plus a horizontal slider with labeled min/max endpoints and a single pointer at the estimated value. Presented as a finding, not a projection — no "before/after age" or future-age state is shown anywhere in the PDF or Dashboard reference (that concept, if it exists, belongs to a separate "Healthy aging" feature already flagged elsewhere in this project's analysis as its own open item, not this report). See §20 item 4.

---

## 16. Payment Gating / Locked States

🔴 **Not addressed by this document.** The reference is a fully-unlocked sample export — it shows no locked, blurred, paywalled, or partial-preview state anywhere. `api-specification.md`'s existing gating contract remains the sole authority for what renders pre- vs. post-payment; this document describes only the fully-unlocked presentation. A locked-state visual treatment (what a Priority Features table, a Treatment Protocol card, or a feature page looks like pre-payment) still needs to be designed and is explicitly out of scope here.

---

## 17. Capture Model / Photo-Angle Count — Explicitly Not Resolved Here

This document does not take a position on the "3-angle" vs. "seven-pose" question carried across the retired Meridian spec's two Reconciliation Notes. The reference report's photography (frontal, profile, multiple tight crops, a split-face composite, a top-down hairline shot) is consistent with either a small confirmed capture set augmented by CV-driven crops/composites, or a richer capture set — it does not by itself prove either. `photo_capture_spec.md` (`ASM-005`) remains the sole authority on how many angles are actually captured; this document only specifies how the *resulting* photo evidence should be labeled and laid out (§11) once captured.

---

## 18. Accessibility (carried forward, unchanged in substance)

- Every chart (§12) needs a text/tabular equivalent regardless of visual treatment.
- No state may be communicated by color alone — the reference's own restraint (chips are label-plus-text, not color-coded) already satisfies this; do not introduce a color-only score/status signal when implementing.
- All body/heading color pairs must meet WCAG AA contrast on their observed backgrounds once exact tokens (§3.1) are finalized.
- Every photo needs alt text describing what it shows (not a category label repeated verbatim from its badge chip).

---

## 19. Non-Goals

This document does not define: database schema, API endpoints, scoring formulas, CV algorithms, the capture-angle count (§17), payment-gating behavior (§16), image-generation vendor/pipeline, or frontend implementation code.

---

## 20. Open Design Questions

1. **Exact color/type tokens (§3)** — approximated from the reference, not sampled from real assets; needs a design-review pass.
2. **AI-generation disclosure copy for Before/After/Potential images (§11)** — the reference shows none, but this project's standing rule requires one; needs explicit confirmation that the rule still applies (it should).
3. **Treatment Protocol — one phase or several (§14)** — the PDF/Dashboard sample shows only Phase 01; `PHASE2_REQUIREMENTS_ANALYSIS.md` §2.1 documents a separate live-app sample with three phases. Reconcile before implementation.
4. **Facial Age — static finding or interactive/projected (§15)** — reference shows a single current-age read-out only.
5. **Recommendation tier caption (§9.1)** — shown twice, both on the Hair page. Confirm whether it's a general per-section field or Hair-specific.
6. **Priority Features / Feature Evaluation table selection logic (§13.1, §13.2)** — which features/zones qualify, and whether "Feature Evaluation"'s zone list (Forehead, Jawline, etc.) is a distinct taxonomy from the eleven report features.
7. **Locked/pre-payment states (§16)** — entirely undesigned; the reference shows only the fully-unlocked view.
8. **Responsive/mobile behavior (§17-equivalent)** — not evidenced; the reference is PDF and desktop-dashboard only.

---

## 21. Component Inventory

Conceptual only — no filenames or implementation tasks.

| Component | Responsibility |
|---|---|
| **ReportDashboard** | Top-level Dashboard page, assembling everything in §4 |
| **StatTileRow** | The 3-up Overall Score / Evaluated / Analysis Time tiles (§4.2, reused inside the identity card) |
| **PriorityFeaturesTable** | §13.1 |
| **FeatureEvaluationTable** | §13.2 |
| **TreatmentProtocolCard** | §14 |
| **FacialAgeSlider** | §15 |
| **HarmonyRadarChart** | 6-axis, single-series chart (§12.1) |
| **ProjectedPotentialRadarChart** | 11-axis, two-series chart (§12.2) |
| **EvidencePhoto** | A single badge-chipped image, optionally with a line-overlay annotation (§11) |
| **BeforeAfterPair** | Two `EvidencePhoto`s side by side, feature-scoped (§9.1) |
| **HairLossScale** | The illustrated 7-stage strip (§13.3) |
| **FeaturePage** | The reusable per-feature PDF page shell (§9.1) |
| **SummaryCallout** | The sage-green per-feature synthesis box (§9.1) |
| **ClosingRecommendations** | Page 16 (§10) |
| **DisclaimerPrivacyPage** | Page 02 (§5) |
| **IntroductionPage** | Page 03 (§6) |
| **UnderstandingResultsPage** | Page 04 (§7) |
| **ProtocolOverviewPage** | Page 05 (§8) |

---

## 22. Final Consistency Checklist

- [x] All eleven feature areas remain present (`BR-008`/`BR-011`, Eyebrows+Eyes sharing one page).
- [x] Every visual element traces to a directly observed page/component in the reference, or is explicitly flagged 🔵/🔴 where it doesn't.
- [x] The capture-angle question is explicitly deferred, not silently resolved (§17).
- [x] Payment-gating is explicitly out of scope, not silently assumed unlocked-by-default (§16).
- [x] AI-generation disclosure is flagged as a gap to close, not dropped because the reference omits it (§11, §20 item 2).
- [x] No raw internal field names, database IDs, or scoring-signal names appear anywhere in this document's own prose.
- [x] No implementation code has been created in this document.

---

*This document is a design/specification artifact only. It does not implement frontend components, generate PDF/rendering code, or modify application code, database, API, architecture, or scoring documents. It is authorized directly by Nishant (2026-09-15) to treat `MyFace-Protocol-test-1 (3).pdf` as the binding visual/structural target, superseding the retired Meridian system.*