# PHASE2_REPORT_DESIGN_SPEC.md
### AI Facial Analysis Platform — Phase 2 Enriched Report Design Specification
### Visual system: **Meridian** (alternate design track — not a copy of the prior draft)

**Status:** Design specification — visual/structural/UX design only, not an implementation artifact
**Legend:** ✅ Confirmed (from upstream documents) · 🔵 Proposed (design recommendation, not stakeholder-confirmed) · 🔴 TBD / open decision

---

## 0. Document Purpose, Authority, and Relationship to the Prior Draft

This document defines the **visual, structural, presentation, and UX design** of the Phase 2 enriched facial-analysis report under a distinct visual system, codenamed **Meridian**. It answers the same question the earlier design pass answered — *"what should the Phase 2 report look like and how should its information be presented?"* — but is written as an independent pass: its own section order, its own component names, and, most visibly, its own color and iconography system. It is not a find-and-replace of the earlier document. Where the two happen to reach the same conclusion (e.g., the eleven feature areas, the seven poses, the score/confidence separation rule), that is because both are constrained by the same upstream requirements, not because one copied the other.

It does not define where data comes from (a future `PHASE2_REPORT_DATA_MAPPING.md`) or exactly what text the LLM generates (`PHASE2_REPORT_TEMPLATE.md`, the companion document to this one).

**Authority order consulted (highest first) — unchanged from the project's existing convention:**

1. `PHASE2_REQUIREMENTS_ANALYSIS.md` — finalized Phase 2 requirements baseline
2. `PHASE2_BRD.md`
3. `PHASE2_PRD.md`
4. `PHASE2_SCORING_SPEC.md`
5. `PHASE2_ARCHITECTURE.md`
6. `PHASE2_DATABASE.md`
7. `PHASE2_API_SPEC.md`

**Phase 1 documents consulted for continuity of meaning (not visual continuity):** `REPORT_DESIGN_SPEC.md`, `REPORT_TEMPLATE.md`, `REPORT_DATA_MAPPING.md`, `PROJECT_OVERVIEW.md`, `CLAUDE.md`, `ONBOARDING_QUESTIONNAIRE_SPEC.md`, and `client_requirements.md`'s confirmation that **no client branding assets exist for this project (CON-003)** — the team owns the visual system. That last point is what licenses Meridian to fix real color and type tokens rather than describing colors only in the abstract.

`PHASE2_VISION_REFERENCE.md` and any external benchmark report remain non-authoritative, consistent with the posture already established for this project: reference material never overrides a decision confirmed in the seven documents above.

**This document does not:** modify application code, generate PDF/rendering code, modify any database/API/architecture/scoring document, modify any Phase 1 report document, or invent new Phase 2 product requirements. It produces exactly one artifact: `docs/report/PHASE2_REPORT_DESIGN_SPEC.md`.

---

## 1. The Meridian Design System Foundation

This is the one section with no equivalent in the prior draft, and it exists specifically so that color and iconography stay consistent across every component described later — every subsequent section pulls its color and icon references from here rather than inventing new ones page by page.

### 1.1 Why a named, fixed-token system (a deliberate, minor divergence)

The prior design pass deliberately avoided fixed hex values, describing color only as an abstract "role-based" system. That is a defensible choice, but with no client branding constraint in place (`client_requirements.md` CON-003), Meridian instead fixes concrete tokens once, here, and every component references the token name — never a raw hex value — so a page built from this spec cannot drift from a page built six months later. This is the single largest visible difference between the two design passes, and it is intentional. 🔵

### 1.2 Color Tokens

| Token | Role | Value | Usage discipline |
|---|---|---|---|
| `ink.primary` | Body and heading text | `#2B2822` (warm charcoal, not pure black) | All running text |
| `ink.muted` | Captions, footnotes, metadata | `#6B6558` | Never for a primary finding |
| `surface.paper` | Page background | `#FAF7F1` (warm ivory) | Every page, web and PDF |
| `surface.card` | Card/panel fill | `#FFFFFF` | Cards sit slightly lighter than the page |
| `surface.recessed` | Locked-state and placeholder fill | `#EFEAE0` | Never used for real content |
| `accent.primary` | The one emphasis color per page | `#A8461F` (terracotta) | Overall score numeral, active nav state, unlock CTA — scarce by rule (§1.5) |
| `accent.secondary` | Structural accent — dividers, icon strokes, chart line | `#3E6E64` (deep juniper) | Icons, chart geometry, section rules — never for body text |
| `state.positive` | Strength / high-confidence framing | `#5C7A52` (moss) | Muted; never bright green |
| `state.notice` | Caution / medium-confidence framing | `#B98A3E` (ochre) | Muted; never bright yellow |
| `state.reserved` | "Raise with a professional" framing only | `#96432E` (rust) | Reserved for the Alert/Flag Card only — see §15.2 |

**The six-color-per-page ceiling is unchanged in principle from the prior draft** — no single page may use more than six of the above tokens plus `ink.primary`/`surface.paper`. This is a governing rule, not a suggestion, because it is what keeps the "calm confidence" tone the client's requirements imply (informational, non-alarmist framing, per `client_requirements.md` FR-004, FR-012).

### 1.3 Typography Tokens

| Token | Typeface role | Usage |
|---|---|---|
| `type.display` | A warm serif for the cover title and section dividers only | Cover, section-opener headers |
| `type.heading` | A humanist sans, medium weight | H1–H3 |
| `type.body` | The same humanist sans, regular weight | Body copy, captions |
| `type.numeral` | A monospaced or tabular-figure face | Score numerals, chart axis values, page numbers — so figures always align in a column |

Exact typeface families are an implementation choice deferred to frontend/PDF tooling; what is fixed here is the **four-role system itself** — display, heading, body, numeral — and the rule that numerals never borrow the body typeface, so a score is always visually distinct from prose around it. 🔵

### 1.4 Icon System

**One icon library, one weight, one stroke width, used everywhere.** 🔵 Proposed: a single outlined icon set (e.g., a Phosphor- or Feather-style regular-weight, 1.5px-stroke library), with exactly one exception — the Confidence Indicator's dot glyph (§1.6), which is the only filled icon shape permitted in the system, precisely so confidence reads as visually distinct from every other icon in the report.

Icon usage is restricted to: feature-area icons (one per feature, in the Feature Header), the lock glyph (locked-state components), the evidence-category badges (§9), and the Confidence Indicator. Icons are never decorative filler — an icon that does not carry one of those four meanings does not appear.

### 1.5 The Accent-Scarcity Rule (carried forward, restated for Meridian's tokens)

`accent.primary` (terracotta) is reserved for **one** load-bearing element per page — the overall score numeral, an active navigation state, or an unlock call-to-action, never more than one of these categories active at once on a single page. This is the same governing principle the prior draft stated ("if it appears everywhere it stops signaling importance"), now expressed against Meridian's specific token rather than an abstract accent role.

### 1.6 The Confidence Indicator Glyph (new, minor structural addition)

Rather than a text-only badge, Meridian defines one small reusable glyph for confidence, always paired with its text label (never color- or glyph-only, per §20):

- **High** — a filled dot (●) in `ink.primary`
- **Medium** — a half-filled dot (◐) in `ink.primary`
- **Low** — a hollow dot (○) in `ink.primary`

The glyph is intentionally monochrome (never colored by confidence level) so a reader cannot mistake confidence-coding for score-coding — reinforcing the score ≠ confidence separation required by the scoring specification (§10.1 below) through a visual choice, not just a layout choice.

### 1.7 Spacing and Shape Tokens

One corner radius (`radius.card`, a moderate rounded-rectangle, applied to every card, image tile, and badge without exception) and one spacing scale (a consistent step used for all vertical rhythm between components). As with the prior draft, no second radius or ad hoc spacing value is introduced anywhere in this document — consistency comes from having exactly one of each, not from choosing "tasteful" one-off values per component.

---

## 2. Preserving What Phase 1 Already Established

Meridian **replaces the Phase 1 visual token values** (§1) but does not reopen Phase 1's structural design philosophy or its non-visual rules. The following carry forward unchanged in substance, restated here so this document is self-contained:

| Element | Treatment under Meridian |
|---|---|
| Design philosophy (evidence-first, calm/non-alarmist tone, print-first, one component vocabulary reused everywhere) | ✅ Unchanged in substance; Meridian is a new token set applied to the same philosophy |
| Grid system, print-safe margins | ✅ Unchanged |
| Component library shape (Information Card, Metric/Score Card, Analysis Card, Recommendation Card, Summary Card, Alert/Flag Card, Badge, Tag, Divider, Callout, Section Header, Feature Header) | ✅ Unchanged component *set*; every one of them now draws its color/type/icon from §1 instead of the prior token values |
| Image guidelines (consistent crop ratios per pose type, captioning, one annotation-overlay color, no beautifying filters) | ✅ Unchanged rule; the one overlay color is now `accent.secondary` (§1.2) |
| Three-tier recommendation priority system | ✅ Unchanged — no new tier |
| Four-category Closing Summary (Key Takeaways, Strengths, Areas for Improvement, Next Steps) | ✅ Unchanged structure |
| Accessibility baseline (contrast, non-color-only signaling, alt text, tagged PDF) | ✅ Unchanged; extended in §20 |
| Print/PDF unbreakable-unit rules | ✅ Unchanged; extended in §17 |

No Phase 1 or prior-draft **structural or content** decision is reopened here without a cited reason. Every genuine visual difference in this document traces back to §1's token system, not to a reinterpretation of what the report must contain.

---

## 3. Report Information Architecture

### 3.1 Section Order — Reorganized Around Three Reading Passes

🔵 Meridian groups the report into three explicit reading passes rather than a flat page list, because the client's requirements describe two very different audiences reading the same document at two different depths (a skimmer checking the overall score pre-payment, and an engaged reader working through all eleven features post-payment):

**Pass One — Orientation** (cover through evidence overview, read in under two minutes)
1. Cover
2. Disclaimer
3. Introduction
4. Table of Contents
5. Overview (overall score, confidence, chart, highlights)
6. Multi-Pose Evidence Overview

**Pass Two — Depth** (the eleven feature sections, read at leisure, typically post-payment)
7. Eleven Feature Analysis Sections

**Pass Three — Synthesis** (closing through appendix)
8. Closing Summary
9. Closing Page / Appendix
10. Report metadata / footer

This is the same eleven-section content set as the prior draft in the same relative order — the "three passes" framing is a presentational and navigational device (§16.2's sticky navigation groups by pass), not a reordering of which section comes before which.

### 3.2 Rationale

Unchanged from the project's established reasoning: the overall score and chart belong on the Overview page because the overall score is a confirmed pre-payment preview concept, and the seven-pose gallery sits once, up front, rather than repeating inside every feature section, because the evidence set is common to all eleven features. All eleven feature sections render regardless of `scoring_status` or evidence completeness — this is a hard rule carried forward unmodified (§13.4).

---

## 4. Cover

Meridian's cover keeps the same content hierarchy the project has already settled on (title > user name > date/metadata), rendered in `type.display` for the title only, everything else in `type.heading`/`type.body`.

| Candidate element | Include? | Reasoning |
|---|---|---|
| Logo, title, user name, generation date | ✅ Include | Baseline requirement, unchanged |
| De-emphasized reference code | 🔵 Include | Support/reference value; rendered in `type.numeral`, `ink.muted` — never the raw internal analysis ID |
| Front Face hero image | 🔵 Optional | A Phase 2 extension enabled by the validated seven-pose set; if rejected, the cover reverts to a photo-free treatment with no other impact |
| Overall score, confidence, or synthesis sentence | ❌ Exclude | These belong on the Overview page (§5); putting them on the cover would fragment the Overview into two places |

**Meridian-specific treatment:** the cover uses exactly one accent touch — a single `accent.primary` rule (a thin horizontal divider beneath the title) — and nothing else on the page carries color beyond `ink.primary` on `surface.paper`. This is a visibly different cover *treatment* from a prior pass that might use a full-bleed hero photo as its primary device; here restraint itself is the differentiator. 🔵

**Do not expose:** internal database IDs, storage keys, CV model or vendor names, or internal scoring signals — unchanged hard rule.

---

## 5. Overall Score Presentation

Authority: score meaning and payment visibility are fixed upstream (`PHASE2_SCORING_SPEC.md` §4/§11/§14–15; `PHASE2_REQUIREMENTS_ANALYSIS.md` §11; `PHASE2_API_SPEC.md` §13/§22.1) and are not renegotiated by a visual redesign.

### 5.1 What Is Shown

- **Overall score** — a large `type.numeral` figure in `accent.primary`, on a 0–100 scale pending final confirmation (🔴, unresolved upstream regardless of visual system — see §25).
- **Overall confidence** — the Confidence Indicator glyph (§1.6) plus its text label, positioned adjacent to but visually separated from the score numeral by a vertical rule — never merged into a single figure like "74 (85%)".
- **Interpretation text** — a short synthesis sentence in `type.body`; its exact wording is a `PHASE2_REPORT_TEMPLATE.md` content concern, not this document's.
- **Scoring version** — never prominent; if surfaced at all, it lives in the footer's existing metadata line in `ink.muted`, `type.numeral`.

### 5.2 Hard Rules (unchanged in substance, restated against Meridian tokens)

- Score and confidence are never visually collapsed into one number.
- No star ratings, beauty iconography, or superlative badge copy — Meridian's icon system (§1.4) has no "beauty" glyph and none may be introduced.
- A missing overall score (legacy analyses) simply omits the score element; the interpretation sentence stands alone.
- Low-score framing never borrows `state.reserved` (rust) — that token is reserved exclusively for the Alert/Flag Card's professional-referral use (§15.2). A modest score uses neutral `ink.primary`/`ink.muted`, never a "warning" color.

### 5.3 Payment Visibility

✅ Confirmed: overall score and confidence render pre-payment. See §14 for the full gating table.

---

## 6. The Harmony Chart

Authority: `PHASE2_REQUIREMENTS_ANALYSIS.md` §11; `PHASE2_SCORING_SPEC.md` §20; `PHASE2_API_SPEC.md` §17.

### 6.1 Purpose and the Non-Negotiable Boundary

Unchanged: the chart is a pure presentation layer over `scoring.feature_scores`. It never computes, estimates, normalizes, or fills in a value. A `null` score is never plotted as `0`, and no synthetic value is invented to keep the shape looking complete. This governs every visual choice below and cannot be overridden by a layout preference.

### 6.2 Meridian's Rendering Choice

🔵 The chart renders as a radar/polygon using `accent.secondary` (juniper) for its outline and fill, at low fill-opacity, with `type.numeral` value labels at each vertex — never left for the reader to infer from shape alone. An axis with no numeric score (structurally non-scorable, or insufficient evidence for this analysis) renders as a hollow, dashed vertex in `ink.muted` with a short non-numeric label, never plotted at the origin (which would read as the worst possible score) and never given a numeric-looking position.

Axis labels use full feature-area names, never abbreviations. Which features receive an axis at all remains governed by the finalized scoring methodology (🔴, open upstream — see §25); this document does not pre-decide the scorable-feature set.

### 6.3 Surface Behavior

| Surface | Behavior |
|---|---|
| Web | Interactive — hover/tap surfaces feature name, score, and Confidence Indicator in a tooltip |
| PDF | Static — every value (or its unavailable-state label) is a permanent adjacent label |
| Mobile | Compact label pattern (icon + abbreviated tap target) rather than shrinking or truncating names below the accessible minimum |
| Accessibility | A text/tabular equivalent (feature → score-or-unavailable-state → confidence) always accompanies the chart |

### 6.4 Payment Visibility

✅ Confirmed: pre-payment the chart renders as a locked, generic (non-data-bearing) placeholder shape in `surface.recessed` — never a low-opacity rendering of real values, which would leak data through the blur. Post-payment, the full chart renders from complete `feature_scores`.

---

## 7. Multi-Pose Evidence Overview

Authority: `PHASE2_REQUIREMENTS_ANALYSIS.md` §6 (seven mandatory poses, fixed and unchanged: Front Face, Left Profile, Right Profile, Left 45°, Right 45°, Smile, Top of Head).

### 7.1 Meridian's Layout

🔵 Rather than a uniform contact-sheet grid, Meridian gives Front Face a distinct, larger tile (it is the pose most feature sections reference) and arranges the remaining six as a smaller uniform row beneath it — a "hero plus strip" layout rather than a flat 2-row grid. This is a minor, genuinely different layout decision from a flat grid, while preserving the same seven images, same captions, and same "Original Photo" category badge (§9).

Each tile carries the Original Evidence badge (§9.1) in the corner using `accent.secondary` on a small `surface.card` chip — the single, consistent visual marker that recurs on every original-evidence image throughout the report.

### 7.2 Responsive / PDF Behavior

| Surface | Behavior |
|---|---|
| Desktop | Hero tile + 2×3 strip |
| Mobile | Hero tile full-width, strip becomes a 2-column stack |
| PDF | Kept to one page at legible size where possible; otherwise split across two adjacent pages along the strip boundary, never mid-row |

### 7.3 Hard Boundary

This gallery contains **only** original validated pose images — no crops, no annotations, no AI-generated content, and it does not imply that every feature section must display all seven images (§8.2 defines the feature-appropriate subset).

---

## 8. Feature Section Design

Authority: `PHASE2_REQUIREMENTS_ANALYSIS.md` §8 (pose-to-feature traceability), §10.

### 8.1 Reusable Structure

Extends the same nine-part structure the project has already established for a feature section — header, score/status card, summary, detailed findings, relevant evidence, optional derived visuals, multi-angle notes, recommendations, optional Before/After — with every visual element now drawing from §1's tokens. No new field is invented and none is removed; this section's job is presentation, not content architecture (that belongs to `PHASE2_REPORT_TEMPLATE.md`).

### 8.2 Feature-Appropriate Evidence (reproduced verbatim in mapping, unchanged)

| Feature | Relevant pose(s) |
|---|---|
| Hair | Front Face + Top of Head |
| Brows | Front Face + Left/Right 45° (where useful) |
| Eyes | Front Face + Left/Right 45° + Smile (where useful) |
| Nose | Front Face + Left Profile + Right Profile + 45° views (where useful) |
| Cheeks | Front Face + Left/Right 45° |
| Jaw | Front Face + Left/Right Profiles + Left/Right 45° |
| Lips | Front Face + Smile + Profile views (where relevant) |
| Chin | Front Face + Left/Right Profiles |
| Skin | Multiple usable facial views |
| Neck | Front Face + Left/Right Profiles |
| Ears | Left Profile + Right Profile |

This table is a presentation-layer restatement only; it does not define or constrain CV algorithms or measurement routing. If a pose is unavailable for a specific analysis, it is simply omitted from that section's evidence strip — this never blocks the section from rendering (§21).

### 8.3 Meridian's Feature Header Treatment

🔵 Each feature section opens with a compact header bar: the feature's single icon (from §1.4's one library) in `accent.secondary`, the feature name in `type.heading`, and — only where elevated — a Priority badge using `ink.primary` text on `surface.recessed`, never a loud color, consistent with the project's existing "descriptive, not alarming" tone requirement.

### 8.4 Sections Are Not Uniform

A section with no derived evidence and no Before/After eligibility is still complete — unchanged rule. Sections are not required to have identical asset counts.

---

## 9. Evidence Categories

Authority: this is the single most load-bearing visual rule in the document — it is the mechanism that prevents a reader from mistaking a generated image for measured evidence, per `PHASE2_REQUIREMENTS_ANALYSIS.md` §12's confirmed constraint.

### 9.1 The Three Categories and Their Meridian Badges

| Category | Source | Badge treatment |
|---|---|---|
| **A. Original Evidence** | The seven validated pose images | A small corner chip, `accent.secondary` on `surface.card`, icon + "Original Photo" label (exact copy 🔴, open — see §25) |
| **B. Derived Evidence** | Optional crops/annotations | Same chip shape, `ink.muted` on `surface.recessed` — a visually *quieter* badge than category A, signaling "a view of the original," always captioned with its source pose |
| **C. AI-Generated Visualization** | Before/After "After" images | A **persistent, high-contrast band** — not a corner chip — spanning the full width of the image, `surface.card` text on `accent.primary`, the only place in the entire system where `accent.primary` appears on something other than the overall score or a CTA. This deliberate exception is what makes category C unmistakable: it is visually louder than every other element in the report by design. |

Category C's badge treatment breaking the accent-scarcity rule (§1.5) on purpose is Meridian's clearest structural safety decision: the AI-generation disclosure is engineered to be the single most visually prominent non-score element on any page it appears on, never something a reader could crop out or overlook.

### 9.2 The Core Rule (unchanged)

The user must never reasonably mistake an AI-generated visualization for original evidence. Category A and B assets never borrow category C's badge treatment, even decoratively, and the three categories are never merged into one undifferentiated image gallery.

---

## 10. Feature Score States

Authority: `PHASE2_SCORING_SPEC.md` §12/§15/§16/§20; `PHASE2_API_SPEC.md` §15.2/§16.

### 10.1 The Three States

| State | Meaning | Meridian presentation |
|---|---|---|
| **Scorable with score** | Numeric score + confidence exist | `type.numeral` score in `ink.primary` (not `accent.primary` — accent is reserved for the overall score only, §1.5) + Confidence Indicator glyph |
| **Structurally non-scorable** | No validated methodology exists for this feature at all | A hollow-dot glyph with a neutral, non-numeric label — never blank, never `0` |
| **Scorable, insufficient evidence** | Methodology exists; this analysis's evidence was insufficient | A distinct dashed-outline treatment, visually different from the structural case above |

Exact copy for both non-numeric states is 🔴 open upstream (see §25); this document fixes only that the two states are visually and textually distinguishable from each other and from a scored state.

### 10.2 Hard Rules

- A missing score never renders as `0`, an empty progress element, or blank space.
- All eleven sections render regardless of `scoring_status`.
- Confidence only appears alongside an actual score — a non-scorable or insufficient-evidence state shows no confidence glyph at all.

---

## 11. Derived Crops and Annotations

Authority: `PHASE2_API_SPEC.md` §19.1 (optional, P1).

Rendered per §9.1's category B badge. The design must render correctly for every combination — none, crop only, annotation only, both, or a different mix per feature. **Missing derived evidence must never produce a placeholder, an error state, or broken spacing** — the section's evidence strip simply contains fewer tiles; the layout adapts rather than reserving empty space for an asset that does not exist. This is never blocking for report generation, PDF generation, payment unlock, or section rendering.

---

## 12. Before/After Visualization

Authority: `PHASE2_REQUIREMENTS_ANALYSIS.md` §12; `PHASE2_API_SPEC.md` §20–21.

### 12.1 Selectivity

Shown only for features present in `before_after_available_features` — a feature with no eligible cosmetic recommendation simply has no Before/After block, not a "not applicable" placeholder. The rest of that feature's section is fully present regardless.

### 12.2 Meridian's Layout

- **Before** — reuses the same Original Photo tile already established for that feature (§9.1-A), not a re-fetched asset.
- **After** — carries the full-width category-C band (§9.1) at all times, plus a short caption reinforcing "illustrative, not guaranteed."
- **Desktop:** side-by-side, equal frames, a single `accent.secondary` divider rule between them labeled "Before" / "After" in `type.numeral`-style small caps for visual distinction from body copy.
- **Mobile:** stacked, Before above After, same labels.
- **PDF:** kept together as one unbreakable unit across a page break.

### 12.3 Generation States

| State | Presentation |
|---|---|
| Pending/generating | A small inline indicator; rest of the section fully visible and unaffected |
| Generated | Full comparison per §12.2 |
| Failed | An isolated, short, non-alarming note scoped to that block only — never implies the analysis itself failed, and never propagates any warning styling outside that one block |

### 12.4 Payment Visibility

✅ Confirmed: pre-payment, Before/After shows only a locked preview signal — both frames obscured behind `surface.recessed`, no images, no generation status.

---

## 13. Locked / Unlocked Presentation

Authority: `PHASE2_API_SPEC.md` §22.1.

### 13.1 Gating Table

| Content | Pre-payment | Post-payment |
|---|---|---|
| Overall score / confidence | ✅ Visible | ✅ Visible |
| Feature-level scores | 🔒 Locked | ✅ Full |
| Harmony chart | 🔒 Generic locked placeholder | ✅ Full |
| Detailed written analysis (11 features) | 🔒 Locked | ✅ Full |
| Before/After | 🔒 Locked preview signal only | ✅ Full |
| Original/derived visual evidence | 🔴 Not resolved upstream — this document follows the conservative default (locked pre-payment) pending confirmation | ✅ Full |
| PDF download | 🔒 Locked | ✅ Available |

### 13.2 Meridian's Locked-State Treatment

Every locked element uses `surface.recessed` fill plus a lock glyph (from the single icon library, §1.4) **and** a short text label — never blur or color alone, per §20. A locked chart is a generic, non-data-bearing polygon shape, never an obscured rendering of the true values (§6.4). A locked score shows the lock glyph in place of a numeral, never a fabricated placeholder number.

### 13.3 Non-Leakage Principle

No locked-state treatment may partially expose real data through low-opacity rendering, size hints, or shape that approximates the true value.

---

## 14. Recommendation Presentation

Authority: `PHASE2_REQUIREMENTS_ANALYSIS.md` §13.

Unchanged three-tier system (Priority / Recommended / Consider), presented through the existing Recommendation Card, restyled with §1 tokens. The design must never, through iconography or color, frame a recommendation as diagnosis, surgical planning, disease detection, or a guaranteed outcome — no clipboard/stethoscope icon exists in Meridian's one library, and `state.reserved` (rust) is reserved exclusively for the Alert/Flag Card's "raise with a professional" framing, never for cosmetic-recommendation emphasis. No phased "Stage 1 / Stage 2" clinical-journey structure is introduced.

---

## 15. Closing Summary

The existing four fixed categories (Key Takeaways, Strengths, Areas for Improvement, Next Steps) are unchanged and sufficient. Any use of scoring data to inform which items surface draws only from already-computed `feature_scores`/`overall_score_contributing_features` — no new ranking formula is defined here. "Areas for Improvement" uses descriptive framing (never "Top weaknesses" or similarly deficit-focused language), consistent with the calm, non-alarmist tone this whole system is built around.

---

## 16. Web Report Design

### 16.1 Layout

A single centered content column (unchanged 2-column ceiling), reflowed for screen.

### 16.2 Meridian's Three-Pass Navigation (new, tied to §3.1)

🔵 A sticky navigation strip groups by the three reading passes defined in §3.1 — **Orientation / Depth / Synthesis** — rather than listing all eleven feature names individually, which keeps the navigation short and legible even as the report grows to eighteen-plus sections. Clicking "Depth" expands the eleven feature names as a sub-list.

### 16.3 Behavior

| Element | Behavior |
|---|---|
| Evidence gallery | Hero + strip on desktop (§7.1), stacked on mobile |
| Chart | Interactive on web, static in PDF |
| Before/After | Side-by-side desktop, stacked mobile |
| Locked states | Rendered inline in normal page position — the reader sees the report's real shape and length |
| Missing optional assets | Section renders with only what exists, no reserved empty space |

---

## 17. PDF Report Design

Same page format, header/footer, disclaimer, and closing-page conventions as the established baseline. New pagination rules for Meridian-specific components:

| Section | Rule |
|---|---|
| Overview (score + chart) | Chart and its legend never split across a page break |
| Evidence overview | Hero tile plus strip kept together where legible; otherwise split along the strip boundary, never mid-row |
| Feature sections | Never split a Recommendation Card; never orphan a Feature Header from its Score/Status Card; images stay with captions |
| Before/After pairs | One unbreakable unit |
| Score/Status Card in any non-numeric state | Never split from its Feature Header |

No PDF-generation library or implementation technology is specified.

---

## 18. Branding Discipline

Meridian's tokens (§1) are the entire branding system — there is no second palette or icon set anywhere in the report. The accent-scarcity rule (§1.5) is the branding rule that most directly protects the report's calm tone: `accent.primary` never appears more than once per page's worth of load-bearing meaning, with the single documented exception of the category-C evidence badge (§9.1), which breaks scarcity on purpose as a safety mechanism, not a branding inconsistency.

---

## 19. Component Inventory

Conceptual only — no React components, filenames, or implementation tasks.

| Component | Responsibility |
|---|---|
| **ReportCover** | Title hierarchy, optional Front Face hero, single accent rule (§4) |
| **OverallScoreCard** | Large numeral + interpretation text (§5) |
| **ConfidenceIndicator** | The dot glyph + label, always paired with a score (§1.6, §5, §10) |
| **HarmonyChart** | Radar rendering from `feature_scores`, unavailable-axis handling, text/tabular fallback (§6) |
| **PoseEvidenceGallery** | Hero + strip seven-pose layout with Original Photo badges (§7) |
| **FeatureSection** | The reusable per-feature container (§8) |
| **FeatureScoreCard** | One feature's score/confidence or non-numeric state (§10) |
| **EvidenceStrip** | The feature-scoped pose subset (§8.2) |
| **DerivedEvidenceTile** | Optional crop/annotation, gracefully absent when none exists (§11) |
| **BeforeAfterComparison** | The pair, with mandatory category-C banding and per-state handling (§12) |
| **RecommendationCard** | Unchanged tiering, restyled (§14) |
| **LockedContent** | Generic locked treatment, non-leaking (§13) |
| **DisclaimerSection** | Standing disclaimer, extended inline labelling for Before/After |
| **ReportFooter** | Metadata, optional `scoring_version` line |

---

## 20. Accessibility

- All Meridian tokens meet WCAG AA contrast on `surface.paper` and `surface.card`.
- Confidence and score-state are never communicated by glyph or color alone — always paired with a text label (§1.6, §10).
- The Harmony Chart always has a text/tabular fallback (§6.3).
- Every image (original, derived, generated) has alt text carrying its category label so a screen-reader user gets the same A/B/C distinction a sighted reader gets from the badges in §9.1.
- Locked elements always carry a text/icon lock indicator, never blur alone (§13.2).
- The category-C band (§9.1) meets the same contrast and minimum-size rule as any other caption — it is never rendered in a low-contrast or decorative way that would undermine its disclosure purpose.
- No color pair (e.g., green/red) alone communicates good/bad anywhere in the system — every state pairs color with text or an icon.

---

## 21. Empty, Unavailable, and Failure States

| State | Behavior |
|---|---|
| Feature score unavailable (either cause) | Distinct non-numeric treatment, section still renders fully (§10) |
| No derived crop/annotation | Evidence strip simply omits it, no placeholder (§11) |
| Feature not eligible for Before/After | Block absent entirely, not "not applicable" (§12.1) |
| Before/After pending | Lightweight in-section indicator, rest of section unaffected (§12.3) |
| Before/After failed | Isolated note, never implies report/analysis failure (§12.3) |
| Legacy Phase 1 report | No Meridian scoring/chart/gallery/Before-After elements render at all — see §22 |

**Governing principle:** the report must never look broken or failed when optional Phase 2 content is missing.

---

## 22. Legacy Phase 1 Compatibility

The report conditions its rendering on the `capture_model: "legacy" | "phase2"` discriminator. For `capture_model: "legacy"`, the report renders exactly per the existing, unmodified Phase 1 design — this document does not alter that rendering. A legacy report never shows a fabricated score, an empty chart, seven-pose placeholders, or Before/After placeholders. Phase 2/Meridian presentation activates only for `capture_model: "phase2"` — there is no partial/hybrid state.

---

## 23. Design Traceability Matrix

| Design Element | Source Requirement | Locked/Unlocked | Optional? |
|---|---|---|---|
| Overall score | `PHASE2_REQUIREMENTS_ANALYSIS.md` §11 | Visible pre-payment | No |
| Confidence | `PHASE2_SCORING_SPEC.md` §15 | Visible pre-payment (overall only) | No — display form 🔴 open |
| Feature scores | `PHASE2_SCORING_SPEC.md` §12 | Locked pre-payment | State always present; value may be absent |
| Harmony chart | `PHASE2_REQUIREMENTS_ANALYSIS.md` §11 | Locked pre-payment | Yes (P1 visualization) |
| 7-pose overview | `PHASE2_REQUIREMENTS_ANALYSIS.md` §6 | 🔴 Unresolved | No — all 7 mandatory |
| 11 feature sections | `PHASE2_REQUIREMENTS_ANALYSIS.md` §3/§10 | Locked pre-payment (content) | No |
| Derived crops/annotations | `PHASE2_REQUIREMENTS_ANALYSIS.md` §15 | Locked pre-payment | Yes |
| Before/After | `PHASE2_REQUIREMENTS_ANALYSIS.md` §12 | Locked preview pre-payment | Yes, selective |
| Recommendations | `PHASE2_REQUIREMENTS_ANALYSIS.md` §13 | Locked pre-payment | No |

---

## 24. Non-Goals

This document does not define: database schema, API endpoint implementation, scoring formulas, CV algorithms, pose validation thresholds, LLM prompts, exact report field paths, JSON data mapping, image-generation provider, PDF-generation library, frontend implementation code, or task-list entries.

---

## 25. Open Design Questions

Carried forward from upstream — a different visual system does not resolve a product decision that was never made:

### 🔴 Requires product/stakeholder confirmation
1. **Score scale (0–100 assumed).**
2. **Confidence display wording and whether it is user-facing at all.**
3. **Structurally-non-scorable label copy.**
4. **Insufficient-evidence label copy.**
5. **Exact evidence-category badge copy** ("Original Photo" etc. — Meridian fixes the *visual treatment* in §9.1, not the words).
6. **Pre-payment visibility of original/derived visual evidence** — this document follows the conservative default.

### 🔵 Meridian-specific, implementation-flexible
7. Fixed vs. dynamic chart axis set, pending the finalized scorable-feature list.
8. Hero-plus-strip evidence layout (§7.1) vs. a flat grid — a reasonable alternative, not the only valid one.
9. Front Face hero image on the cover — omittable with no other impact.
10. Exact typeface families under the four-role type system (§1.3).

None of the above reopens an already-confirmed decision — the eleven feature areas, the seven poses, score meaning, and the non-clinical recommendation boundary all remain fixed.

---

## 26. Relationship to Companion Documents

```
PHASE2_REPORT_DESIGN_SPEC.md   = visual/UX presentation, Meridian token system   (this document)
PHASE2_REPORT_TEMPLATE.md       = content/narrative structure
PHASE2_REPORT_DATA_MAPPING.md   = exact source/field mapping                     (future)
PHASE2_SCORING_SPEC.md          = deterministic scoring methodology
PHASE2_API_SPEC.md              = external/client-facing data contract
```

---

## 27. Final Consistency Check

- [x] All 11 feature areas remain present.
- [x] All 7 poses remain unchanged.
- [x] Overall score meaning matches the scoring specification.
- [x] Score and confidence remain visually separate throughout (§1.6, §5, §10).
- [x] Missing score is never displayed as zero.
- [x] The chart never calculates scores — presentation only.
- [x] Non-scorable and insufficient-evidence states are distinctly labeled.
- [x] Original, derived, and generated evidence remain visually distinct, with category C deliberately the loudest element in the system (§9.1).
- [x] Before/After remains selective; failure never fails the report.
- [x] Recommendations remain general/cosmetic, never clinical.
- [x] Payment gating matches the API contract.
- [x] No raw storage/database references are ever shown.
- [x] Legacy Phase 1 reports remain fully compatible.
- [x] Exactly one color/type/icon system (Meridian, §1) is used throughout — no second palette introduced anywhere in this document.
- [x] No implementation code has been created in this document.

---

*This document is a design/specification artifact only. It does not implement frontend components, generate PDF/rendering code, or modify application code, database, API, architecture, or scoring documents. It is subordinate in authority to `PHASE2_REQUIREMENTS_ANALYSIS.md`, `PHASE2_BRD.md`, `PHASE2_PRD.md`, `PHASE2_SCORING_SPEC.md`, `PHASE2_ARCHITECTURE.md`, `PHASE2_DATABASE.md`, and `PHASE2_API_SPEC.md`.*