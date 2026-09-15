# Report Template
### AI Facial Analysis Platform — Enriched Report Content / Template Specification (Milestone 2)
### Companion to `report_design_spec.md` (reference-exact system)

**Status:** ACTIVE — version 3.0 (2026-09-15). Replaces the prior "Meridian"-companion template in full.

**Legend:** ✅ Confirmed (directly observed in the reference) · 🔵 Proposed (a reasonable content rule where the reference doesn't fully specify a mechanic) · 🔴 TBD (a genuine open decision)

---

## 0. Document Purpose and Authority

This document defines **what content belongs on each page of the report, in what order, and under what writing rules** — matching `MyFace-Protocol-test-1 (3).pdf` exactly in structure and substance, per Nishant's direction (2026-09-15, see `report_design_spec.md` §0). It does not define layout, color, or typography (`report_design_spec.md`) or exact data field paths (`database-design.md`).

**One deliberate departure from a literal copy — content-quality rule, not a structural one:** the reference PDF's narrative text exposes raw internal field names verbatim in places — e.g. "crownCoverage is recorded as notable," "a Natural overall scoreLabel with hairColor Black," "neckWidthClass Wide and neckLengthClass Long," "the assessment's scoreLabel Balanced." This document does **not** reproduce that pattern. It is a defect in the reference's own narrative-generation pipeline, not a deliberate design choice, and it directly contradicts this project's own standing rule (carried forward unchanged, §13) that raw technical identifiers are never exposed in user-facing prose. Every content rule below preserves the reference's exact structure, sections, data points, and tone — but phrases attributes in plain English (e.g. "a notable amount of coverage at the crown," not "crownCoverage is recorded as notable").

**Authority order (highest first):**

1. `client_requirements.md`
2. `claude/PHASE2_REQUIREMENTS_ANALYSIS.md` §2.1–§2.7 (prior review of this same reference)
3. `report_design_spec.md` — this document's companion, authoritative for layout/structure; this document does not redesign it
4. This document, for content/copy rules

**This document does not:** modify application code, implement report generation, define database/API fields, or resolve open scoring/capture questions. It produces one artifact: `report_template.md` (this file).

---

## 1. Content Continuity from Phase 1 (unchanged)

| Phase 1 rule | Status |
|---|---|
| Evidence-first explanations — every claim paired with reasoning | ✅ Unchanged |
| Objective, professional, non-judgmental, never-diagnose, never-shame writing | ✅ Unchanged |
| General/cosmetic, non-clinical recommendation boundary | ✅ Unchanged |
| Consistent structure across all eleven feature areas | ✅ Unchanged, restructured per §9 below |
| Standing, non-AI-generated disclaimer, never omitted or shortened | ✅ Unchanged |
| Three-tier recommendation priority (where used) | ✅ Unchanged — not directly visible in the reference's prose, but not contradicted either; see §15 |
| All eleven feature areas always present regardless of evidence completeness | ✅ Unchanged |
| No raw internal field names, scores rendered without qualitative interpretation, etc. | ✅ Unchanged — see §0's departure note above |

---

## 2. Page-by-Page Content Map

Matches `report_design_spec.md` exactly:

| Page | Content |
|---|---|
| Dashboard | §3 |
| PDF p.02 — Disclaimer & Privacy | §4 |
| PDF p.03 — Introduction | §5 |
| PDF p.04 — Understanding the Results | §6 |
| PDF p.05 — "{Subject}'s Protocol" | §7 |
| PDF pp.06–15 — Eleven feature pages | §9–§11 |
| PDF p.16 — Closing Recommendations | §17 |

---

## 3. Dashboard Content

### 3.1 Identity & Stat Tiles
Subject's display name, a human-readable reference code (never the raw internal analysis ID), assessment date, overall score, evaluated-point count, analysis duration. No interpretation text here — numbers and labels only.

### 3.2 "Your Facial Analysis" Explainer
A short (2–3 sentence) plain-language paragraph describing the method (scientific facial analysis and regional assessment grounded in measured morphology) and the three-step framing: measured morphology → projected potential (before/after visualization) → staged protocol (non-surgical phase guidance). This is standing explainer copy, not per-subject narrative — it should read the same across every report.

### 3.3 Priority Features to Improve
For each surfaced feature (the lowest-scoring subset — see `report_design_spec.md` §13.1 for the open selection-logic question): feature name, score, a short qualitative label derived from the score band (e.g. "Needs attention," "Balanced" — never invented per-report, always drawn from a fixed, confirmed label set), and 1–3 plain-language attribute lines. Attribute lines translate structured findings into short noun phrases a reader understands without CV/measurement background — e.g. "noticeably uneven" rather than a raw evenness index, "wide" rather than a raw width classification code.

### 3.4 Facial Age
One sentence of context is optional; the component itself (numeral + slider) carries most of the meaning per `report_design_spec.md` §15. If accompanying text is shown, it states the estimate plainly ("Estimated facial age: 28") without medical framing (not a health claim, not tied to any specific finding elsewhere in the report unless the underlying data genuinely supports that link).

### 3.5 Harmony Profile Chart Caption
A one-line caption naming the chart's six dimensions in plain language (Harmony, Symmetry, Smoothness, Jawline, Skin, Volume) — the chart itself never needs narrative beyond this; per `report_design_spec.md` §12.3, the narrative layer never computes or restates the plotted values as prose elsewhere on the page.

### 3.6 Overview Paragraph
One short paragraph synthesizing the overall-harmony finding (e.g. "This evidence-based non-surgical protocol is grounded in the subject's measured facial analysis (overall harmony described as {qualitative label}), organised around key aesthetic features.") — this is the Dashboard's equivalent of the old Meridian system's "Interpretation text" (§5.1 of the retired spec), same content rule: never a bare number, always a qualitative frame, never invented beyond what the scoring layer actually returned.

### 3.7 Treatment Protocol Card
Phase label and title in plain language (e.g. "Foundation & Photoprotection," not an internal phase-code); a duration/timing line; 2–4 bullet action items, each traceable to a specific finding already shown elsewhere on the Dashboard (not invented independently); a closing paragraph explaining, in prose, why this phase is sequenced first. See §15 for the same non-clinical boundary that governs all recommendation content — a "Treatment Protocol" phase is still cosmetic/non-surgical guidance, never a clinical treatment plan, regardless of its name.

### 3.8 Feature Evaluation Table
Zone, a plain-language Finding, and an optional Reference/benchmark value. Where no reference/benchmark exists for a zone, the cell is left empty (an em dash or blank), never a fabricated placeholder value.

---

## 4. Disclaimer & Privacy Content

Standing, legally-reviewed copy — never AI-generated, never omitted, never shortened per report. Must establish, in substance (carried forward unchanged from the retired spec's §5.2, still fully consistent with the reference):

- This is an AI-assisted facial appearance analysis, informational/cosmetic in nature.
- Not a medical diagnosis, clinical assessment, surgical plan, or disease-detection tool.
- Recommendations are general/cosmetic, not treatment.
- Numeric scores are not attractiveness/beauty judgments.
- Any AI-generated Before/After or Potential imagery is a simulation with no guaranteed real-world outcome (see `report_design_spec.md` §11 — the reference itself omits this disclosure inline on photos, but it belongs here on the standing Disclaimer page at minimum, and ideally also inline per `report_design_spec.md` §20 item 2).
- A data-retention statement (bounded retention window for supplied images/video; images are stored as a whole once modified by the platform, not disaggregated).
- A brief note on cookies/analytics and a link to the full privacy policy.
- A one-line commissioning statement naming the subject and the report month/year.

Tone stays calm and confident — no alarming or excessively defensive legal language. Not repeated in full inside any feature section.

---

## 5. Introduction Content

Required: a short statement of method (measurement/cephalometric framing, why this makes findings "less subjective"); a **Limitations** paragraph naming what can affect measurement accuracy (head position, lighting, camera quality, absence of radiographic imaging) plus a restated "not a medical diagnosis" line; a **Contents** list (section name + page number) covering every page from "Understanding the Results" through "Closing Recommendations."

Must not: explain technical implementation (no CV library, model, or vendor names; no internal scoring formulas); state any specific finding, score, or recommendation (those belong to later pages).

---

## 6. Understanding the Results Content

Four fixed, standing principles (not regenerated per report — this is product-level explainer copy, same across every report):

1. The recommendations focus on markers of facial health and harmony, working with the subject's existing features rather than trying to change what makes them distinctive.
2. **This platform does not rate attractiveness.** The assessment highlights what works best for the subject's own features using objective measurement, not a universal beauty standard. This principle must be stated explicitly and on its own — not folded into general disclaimer boilerplate — per `client_requirements.md` FR-004/FR-012.
3. The protocol mixes foundational guidance (SPF, sleep, hydration) with more targeted recommendations — the fundamentals support the effectiveness of the more specific guidance, they aren't filler.
4. All recommendations are informational and aesthetic only; any in-clinic treatment or prescription product should be discussed with a qualified medical professional.

---

## 7. "{Subject}'s Protocol" (Overview) Page Content

Required: a short paragraph on what the protocol is for and how following it supports progress toward the subject's own aesthetic potential (never a promise of a specific outcome); a short paragraph framing the analysis as objective/non-comparative — it highlights the subject's own strengths and areas for improvement rather than measuring against a universal ideal; the fixed eleven-feature list (heading "Projected potential"), presented as a simple checklist of what the report covers, with no per-feature detail yet; a caption for the Projected-Potential-vs-Client-Values chart naming both series in plain language.

### 7.1 The Governing Boundary (carried forward unchanged)

The narrative layer never calculates a score or a chart value — score/chart generation belongs to the deterministic scoring layer; this page only explains what the chart shows. No synthesis statement on this page may be a mechanical concatenation of eleven feature one-liners — it should read as one coherent framing paragraph.

---

## 8. Score and Confidence Language Rules (cross-cutting, carried forward unchanged)

- A high score never implies high confidence and vice versa — keep them visually and textually separate wherever both appear.
- A missing/non-scorable feature is never rendered or implied as "0," "zero," "poor," or "failed" — use plain, neutral language appropriate to why the value is absent (the methodology doesn't apply to that feature at all, vs. this specific analysis's evidence was insufficient — these are two different situations and should read as two different things, not one generic "unavailable" label).
- Confidence, where shown, is a qualitative label, never a numeric percentage.
- A score is never described using beauty/attractiveness language, superlatives, or star-rating language.

---

## 9. The Eleven Feature Pages — Shared Content Rules

### 9.1 Fixed Feature Set and Order (unchanged)

Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears — `BR-008`. Per `BR-011`, "Smile" content (mouth width, smile shape/curvature, teeth exposure, upper smile arc) is folded into Lips as additional sub-fields, never a 12th top-level section — Eyebrows and Eyes sharing one physical page (§10, row 2) does not change the eleven-feature count.

### 9.2 Per-Feature Sub-Sections

Each feature page's sub-sections are fixed per feature (not a uniform template applied identically to all eleven) — see the table in `report_design_spec.md` §9.2 for which sub-headings belong to which feature. Within each sub-section:

- Open with a **concise, evidence-grounded finding** in plain language — what was observed, stated neutrally, never forced toward a positive or negative conclusion.
- Where relevant, note **how the finding relates to the subject relative to typical/peer ranges** (e.g. "wider than typical," "within the balanced range") — comparative, not judgmental, language.
- Where a photo panel accompanies the sub-section (profile shot, annotated analysis image, isolated crop), the prose should be traceable to what that image shows in plain language (e.g. "on profile" or "from the side angle"), never a raw pose/angle identifier.
- Close with a **maintenance-or-change recommendation** consistent with §15's non-clinical boundary — many sub-sections in the reference conclude "no non-surgical changes are recommended; continue current routine," which is a legitimate, complete recommendation in its own right, not a placeholder needing more content.

### 9.3 Recommendation Tier Caption

Where a specific non-invasive/OTC recommendation applies to a sub-section, an optional short caption states its tier in plain language (e.g. "This is a non-invasive, over-the-counter–level recommendation.") — see `report_design_spec.md` §9.1/§20 item 5 for the open question of whether this should appear consistently across all eleven features. Recommend implementing it as available-when-applicable across every feature, not Hair-specific, pending confirmation.

### 9.4 Before/After (per feature)

**Before** identifies the same original evidence already established for that feature elsewhere on the page (reused, not a new asset). **After** is clearly an illustrative simulation — see `report_design_spec.md` §11 and §4's disclosure requirement — explaining, in one short sentence, what change is being illustrated (a styling/grooming/skincare change, never a surgical or medical result) and stating plainly that it's illustrative, not a guaranteed outcome.

### 9.5 Summary Callout

Every feature page ends with a 2–4 sentence synthesis titled `"{Feature} Summary"` or `"{Feature} Region Summary"`: restates the feature's overall character, names the primary non-surgical priority (maintenance vs. a specific change), and never introduces a finding not already stated earlier on the page.

---

## 10. Feature-Specific Content Notes

| Feature | Content specifics |
|---|---|
| **Hair** | Covers style (hairline, forehead exposure, texture, parting, crown coverage/visibility), hair loss (pattern-staging language mapped to the illustrated scale, `report_design_spec.md` §13.3 — described in plain language, e.g. "early-stage, minimal progression," never a raw internal stage code), and hair health (density, coverage, overall condition) as three distinct sub-sections. |
| **Eyebrows + Eyes** | Covers brow shape/density/position, eyelash density/pigmentation and simple maintenance guidance, eye shape/lid contour, and under-eye tone/hollowing — four sub-sections on one page. Content for the two features stays clearly separated by sub-heading even though they share a page. |
| **Nose** | Profile-based description (dorsal contour, alar base width, tip projection) plus a skin-surface-quality angle specific to the nose (pore visibility, shine) since nasal skin texture is a common secondary concern. |
| **Cheeks** | Structural description (cheekbone height/projection, cheek width, jaw-to-cheek transition, symmetry) grounded in the annotated measurement photo — the prose should reference what the measurement lines show without naming the underlying CV technique. |
| **Jaw** | Structural description (mandibular definition, transverse width, gonial angle) plus a distinct "Further Enhancement" sub-section offering grooming/styling ideas (hairstyle, facial hair shaping) that create visual balance without altering anatomy — always framed as styling, never a jaw-altering claim. |
| **Lips** | Volume, philtrum length, cupid's-bow definition, and overall perioral balance — includes folded-in Smile content where evidence supports it (mouth width, smile arc) per `BR-011`, without calling it out as a separate section. |
| **Chin** | Shape, height, width, and projection, plus labiomental-angle framing in plain language ("the crease beneath the lower lip," never "labiomental angle" verbatim unless the audience is expected to know the term). |
| **Skin** | A Skincare Protocol sub-section (texture, tone evenness, redness, under-eye shadowing) with a concrete, tiered at-home regimen (cleanser → moisturizer → sun protection → one targeted active), plus a "Further Skin Enhancement" sub-section for longer-horizon habits (patch-testing new actives, gradual introduction). This is the most regimen-heavy page in the report and should stay OTC/lifestyle-level throughout — never a prescription or in-clinic procedure recommendation. |
| **Neck** | Neck Size (length/width classification in plain language, posture framing) and Neck Skin (texture/laxity where evidence exists; where the platform's photo evidence genuinely can't assess neck skin quality, the content says so plainly rather than guessing — see §13). |
| **Ears** | Symmetry and prominence relative to typical ranges, framed entirely around non-surgical, styling-based balancing (hairstyle, earring choice, eyewear-frame choice) — never a surgical framing (e.g. otoplasty) even when asymmetry is more pronounced. |

---

## 11. Evidence Traceability

Findings should read as traceable to the photo evidence shown on the same page in plain language ("visible on profile," "seen in the frontal comparison") — never a raw pose/angle/measurement identifier, storage key, or database ID. This is unchanged from the retired spec's §13 and remains a hard rule even though the reference itself violates a related rule (raw field names, §0) — the pose/angle-traceability rule was never violated by the reference and stays intact.

---

## 12. Questionnaire Personalization (unchanged)

Where a page references the subject's intake/medical history (e.g. "because medical conditions are reported, a conservative approach is recommended" — observed on the Jaw and Ear pages), this must read as *informed by* the questionnaire, never *measured from* it — questionnaire answers influence emphasis and caution level, never a CV measurement or a score.

---

## 13. Hallucination and Evidence Safety Rules (unchanged, restated)

The narrative layer must not invent: measurements, scores, confidence, asymmetry, proportions, angle/pose observations, questionnaire answers, visual evidence, recommendation eligibility, or Before/After availability. **If evidence is missing, say less** — never compensate for a missing or insufficient value by inventing plausible-sounding content. Raw internal identifiers (field names, storage keys, database IDs, internal scoring-signal names, pose/angle codes) are never exposed in user-facing prose anywhere in the report — this is the rule the reference's own narrative violates (§0) and that this document does not carry forward.

---

## 14. Content Quality Rules (unchanged)

Clear, specific, concise, evidence-grounded, professional, calm, non-judgmental. Avoid repetitive boilerplate, vague filler, unsupported certainty, exaggerated praise or criticism, beauty/attractiveness ranking, clinical terminology, and deterministic promises. Avoid verbatim repetition of the same observation across a sub-section, its Before/After caption, and the closing Summary box unless deliberate reinforcement genuinely helps (e.g. a priority finding re-surfaced in the Summary).

---

## 15. Recommendation Content Boundary (unchanged)

General, cosmetic, appearance-oriented, non-clinical. Allowed: hairstyle/grooming, brow styling, facial-hair styling, skincare presentation, clothing/accessory considerations, other non-clinical appearance guidance — including the Dashboard's "Treatment Protocol" phases (§3.7), which are cosmetic/lifestyle phases, not a clinical treatment plan, regardless of the "Treatment Protocol" name. Must not appear anywhere: diagnosis, prescription-medication advice, surgical planning, disease claims, guaranteed outcomes. Prefer tentative phrasing ("may complement," "could consider") over absolute phrasing ("will fix," "guarantees"). Where no meaningful recommendation is supported by the evidence, the correct response is "no changes are recommended; continue current routine" — a complete, legitimate recommendation, not a gap to fill with generic filler.

---

## 16. Feature Score States (unchanged from retired spec, still applicable)

| State | Narrative treatment |
|---|---|
| Scorable with a numeric score | State the score with qualitative interpretation |
| Structurally non-scorable (no methodology exists for this feature at all) | Plain, neutral language stating the methodology doesn't apply — never implies a failed score |
| Scorable, but this analysis's evidence was insufficient | Distinct wording from the above — never implies the subject did anything wrong, never conflated with "non-scorable" |

---

## 17. Closing Recommendations Content

Four-paragraph synthesis (matching the reference's exact two-column, four-paragraph structure), covering, in order: (1) overall facial harmony and the primary structural/skeletal priorities; (2) the periorbital/eye region and its priorities; (3) hair and lower-face grooming priorities; (4) a practical, sequenced next-steps paragraph plus a closing line restating that the protocol is educational guidance, not medical diagnosis or treatment. Every point made here must trace back to a finding or recommendation already shown earlier in the report — this page never introduces a new finding. Avoid deficit-focused language ("your worst features") in favor of neutral, opportunity-focused framing ("areas with the most practical opportunity for improvement").

---

## 18. Required vs. Optional Content Matrix

| Element | Required/Optional | Fallback |
|---|---|---|
| Overall score, Evaluated count, Analysis time (Dashboard) | Required | N/A |
| Priority Features table | Required if any feature qualifies | Omitted entirely if no feature meets the selection threshold (🔴 threshold TBD, `report_design_spec.md` §13.1) |
| Harmony Profile chart | Required | Text/tabular fallback per `report_design_spec.md` §18 |
| Treatment Protocol card | Required, at least one phase | N/A — see `report_design_spec.md` §20 item 3 for the one-phase-vs-several question |
| Facial Age | Required where the underlying estimate exists | Omitted if no estimate is available |
| Feature Evaluation table | Required | Empty cell (not a fabricated value) where no reference/benchmark exists |
| Disclaimer & Privacy | Required | N/A — never omitted or shortened |
| Each of the eleven feature pages | Required | N/A — always present regardless of evidence completeness |
| Before/After per feature | Required where the underlying generation succeeded | A short isolated note if generation failed or is pending — never blocks the rest of the section |
| Summary callout per feature | Required | N/A |
| Closing Recommendations | Required | N/A |

---

## 19. Open Content Decisions

Carried from `report_design_spec.md` §20 where they have a content-layer dimension:

1. Recommendation tier caption — general field or Hair-specific (§9.3).
2. AI-generation disclosure copy for Before/After/Potential images — needs exact wording (§4, `report_design_spec.md` §11/§20 item 2).
3. Priority Features / Feature Evaluation selection logic and exact qualitative-label set (§3.3, §3.8).
4. Treatment Protocol — confirm one phase vs. several against `PHASE2_REQUIREMENTS_ANALYSIS.md` §2.1's three-phase live-app sample.
5. Locked/pre-payment content states — entirely undesigned (`report_design_spec.md` §16).

---

## 20. Relationship to Companion Documents

```
report_design_spec.md          = layout/visual specification, reference-exact system   (companion)
report_template.md              = content/narrative structure                          (this document)
claude/PHASE2_REQUIREMENTS_ANALYSIS.md = prior review of the same reference PDF/video
database-design.md              = exact source/field mapping
api-specification.md            = external/client-facing data contract, payment gating
```

---

## 21. Final Validation

- [x] Exactly eleven feature areas remain, Eyebrows+Eyes sharing one physical page without becoming a twelfth section.
- [x] Score ≠ confidence, throughout.
- [x] Missing/non-scorable ≠ zero, throughout.
- [x] The narrative layer never calculates scores or chart values.
- [x] No raw internal field names, IDs, or scoring-signal names appear in user-facing prose anywhere (the one deliberate departure from the literal reference, per §0).
- [x] Recommendations remain general/cosmetic, including "Treatment Protocol" phases, never clinical.
- [x] AI-generated Before/After/Potential imagery is flagged as needing disclosure copy even though the reference omits it (§4, §9.4).
- [x] Closing Recommendations introduces no new findings.
- [x] Every page maps to a real page in the reference PDF/Dashboard (§2).

---

*This document is a content/narrative-structure specification only. It does not implement report generation, PDF generation, frontend components, or application code, and does not modify any database, API, architecture, or scoring document, nor `report_design_spec.md`. It is authorized directly by Nishant (2026-09-15) to match `MyFace-Protocol-test-1 (3).pdf`'s content exactly, with the single deliberate exception of natural-language phrasing in place of the reference's raw field-name leakage (§0).*