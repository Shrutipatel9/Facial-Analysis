# PHASE2_REPORT_TEMPLATE.md
### AI Facial Analysis Platform — Phase 2 Enriched Report Content / Template Specification
### Companion to `PHASE2_REPORT_DESIGN_SPEC.md` (Meridian visual system)

**Status:** Content/narrative-structure specification — documentation only, not an implementation artifact
**Legend:** ✅ Confirmed (from upstream documents) · 🔵 Proposed (content recommendation, not stakeholder-confirmed) · 🔴 TBD / open decision

---

## 0. Document Purpose and Authority

This document defines **what content belongs in each section of the Phase 2 enriched report, and what rules the report-generation layer (the LLM narrative layer) must follow when producing it.** It answers *"what should the report say, and under what constraints?"* — not what it looks like (`PHASE2_REPORT_DESIGN_SPEC.md`), not the exact field-by-field data source (`PHASE2_REPORT_DATA_MAPPING.md`, future), not how scores are computed (`PHASE2_SCORING_SPEC.md`), and not the external API contract (`PHASE2_API_SPEC.md`).

Like its design-spec companion, this is an independent writing pass, not a reworded copy of an earlier draft — it reaches the same substantive rules the project has already settled (they are fixed by the same upstream documents) but organizes and phrases them on its own terms, and it cross-references the Meridian components defined in the design spec by name rather than describing generic UI.

**Authority order consulted (highest first):**

1. `PHASE2_REQUIREMENTS_ANALYSIS.md`
2. `PHASE2_BRD.md`
3. `PHASE2_PRD.md`
4. `PHASE2_SCORING_SPEC.md`
5. `PHASE2_ARCHITECTURE.md`
6. `PHASE2_DATABASE.md`
7. `PHASE2_API_SPEC.md`
8. `PHASE2_REPORT_DESIGN_SPEC.md` — this document's companion, authoritative for structure/presentation; this document does not redesign it

**Phase 1 documents consulted for content continuity:** `REPORT_TEMPLATE.md`, `REPORT_DESIGN_SPEC.md`, `REPORT_DATA_MAPPING.md`, `PROJECT_OVERVIEW.md`, `CLAUDE.md`, `ONBOARDING_QUESTIONNAIRE_SPEC.md`, and `client_requirements.md` (FR-009 through FR-012 fix the eleven-feature, non-clinical, tiered-recommendation content baseline this document extends).

**This document does not:** modify application code, implement report generation or PDF generation, modify any database/API/architecture/scoring document, modify any Phase 1 report document, modify `PHASE2_REPORT_DESIGN_SPEC.md`, invent new product requirements, scoring formulas, CV measurements, API fields, or database fields, or resolve open 🔴 product decisions without authoritative support. It produces exactly one artifact: `docs/report/PHASE2_REPORT_TEMPLATE.md`.

---

## 1. Three Gaps Carried Forward, Not Resolved Here

- **Exact label/badge copy** (e.g., the Meridian evidence-category badges defined structurally in the design spec §9.1, or the score-state labels in §10) is intentionally left open there and not finalized here either, because no product/legal sign-off exists for exact user-facing strings. This document fixes the *content rules* that copy must satisfy, not the final wording.
- **Non-scorable and insufficient-evidence wording** remains open per the scoring specification. This document fixes the *distinction* the narrative must preserve (§8.3).
- **Confidence display to end users** remains open. This document writes its rules assuming confidence is shown (the design spec's default posture), and notes that if confidence display is rejected, every confidence-related content rule below simply does not apply, with no other content impact.

---

## 2. Scope

This document defines: section content responsibilities in the order fixed by the design spec §3.1's three-pass structure; content ordering within and across sections; required vs. optional content per section; score explanation placement and the score/confidence separation rule; evidence-reference language rules; the reusable eleven-feature content template; multi-angle observation structure; recommendation content rules; Before/After explanatory content; Closing Summary content; disclaimer microcopy requirements; missing/unavailable-content behavior at the content layer; and AI narrative-generation safety constraints.

It does not define CSS, layout, colors, typography, icons (all `PHASE2_REPORT_DESIGN_SPEC.md`), React or frontend code, database schema, API shapes, exact field paths, scoring formulas, CV algorithms, the image-generation provider, or implementation tasks.

---

## 3. Content Continuity from Phase 1

| Phase 1 content rule | Treatment here |
|---|---|
| Evidence-first explanations — every claim paired with reasoning, never a bare number/label | ✅ Unchanged, extended with multi-pose traceability language (§13) |
| Objective, professional, non-judgmental, evidence-based, never-exaggerate, never-diagnose, never-shame writing rules | ✅ Unchanged in full, extended with score/confidence and AI-generation-labelling language (§18) |
| General/cosmetic, non-clinical recommendation boundary | ✅ Unchanged; extended to Before/After framing (§16) |
| Consistent structure across all eleven feature areas | ✅ Unchanged principle; the template itself gains new fields (§9) |
| Concise per-feature summary before deeper detailed findings | ✅ Unchanged pattern (§10–§11) |
| Standing, non-AI-generated disclaimer, never omitted or shortened | ✅ Unchanged (§5) |
| Three-tier recommendation priority | ✅ Unchanged, no new tier (§15) |
| Four fixed Closing Summary categories | ✅ Unchanged (§17) |
| All eleven feature areas always present regardless of evidence completeness | ✅ Unchanged, reinforced throughout (§9, §20) |
| Confidence shown as a qualitative label, never a numeric percentage | ✅ Unchanged, now formalized against Meridian's Confidence Indicator glyph (§8) |

No Phase 1 content rule is discarded. Every Phase 2 addition either extends an existing content contract or adds a new, additive responsibility.

---

## 4. Content Architecture

Follows the design spec's three-pass information architecture (§3.1 there) without redesigning it:

- **Pass One — Orientation:** Cover (§5.1), Disclaimer (§5), Introduction (§6), Overview (§7–§8), Multi-Pose Evidence Overview (§9)
- **Pass Two — Depth:** Eleven Feature Analysis Sections (§10–§16)
- **Pass Three — Synthesis:** Closing Summary (§17), Closing Page/Appendix (unchanged from Phase 1, not redefined here), Report metadata (unchanged, extended only per the design spec's optional footer note)

---

## 5. Cover and Disclaimer Content

### 5.1 Cover (static, never AI-generated)

Required: report title, user-facing name/identity, generation date, brand text. Optional: a short human-readable reference code, never the raw internal analysis ID (per Meridian's de-emphasized treatment in the design spec §4). Must never appear on the cover: overall score, confidence label, any synthesis sentence, any feature-level content, or any technical/infrastructure detail.

### 5.2 Disclaimer

Standing, legally-reviewed copy — never AI-generated, never omitted, never shortened per report. Must establish, in substance: this is an AI-assisted facial appearance analysis; informational/cosmetic in nature; not a medical diagnosis, clinical assessment, or surgical plan; does not detect disease; recommendations are general/cosmetic, not treatment; numeric scores are not attractiveness/beauty judgments; AI-generated Before/After images are simulations with no guaranteed real-world outcome. Tone stays calm and confident — no alarming or excessively defensive legal language, and the disclaimer is not repeated in full inside every feature section; only the short inline Before/After reminder established in §16.4 recurs.

---

## 6. Introduction Content

Required: a synthesized (never verbatim) statement of what informed the analysis — photo evidence plus questionnaire answers; a statement that the analysis uses multiple validated facial views (the seven-pose capture), not a single photo; a statement that questionnaire context personalizes interpretation and recommendations, not measurements (§14); a statement that the report covers the same eleven feature areas; where scoring is present, a plain-language statement that score and confidence are separate concepts (§8); a statement that recommendations are cosmetic guidance, not medical advice.

Must not: repeat individual questionnaire answers verbatim; explain technical implementation (no CV library names, model/provider names, database or storage architecture, internal scoring formulas); dump raw question IDs; state any specific finding, score value, or recommendation (those belong to the Overview onward).

---

## 7. Overview / Summary of Findings Content

### 7.1 Required Content

Overall score where present; overall confidence where present and where confidence display is adopted (§25 item 2 in the design spec); a short interpretation sentence explaining what the overall score reflects — harmony, symmetry, proportions, feature balance, in neutral non-clinical framing; the Harmony Chart's accompanying context (§9 below is about pose evidence — chart caption content is here); key strengths/highlights; important observations; recommended focus areas cross-referenced to the eleven feature sections.

Optional: a short reference to which features contributed most to the overall score, where the underlying data supports it — narrative acknowledgment only, never a re-derivation of the aggregation itself.

### 7.2 The Governing Boundary

**The narrative layer must never calculate the overall score.** Score generation is the deterministic scoring layer's responsibility; score explanation is this layer's responsibility. The narrative must not modify, round, or recalculate a score; infer or invent a missing feature score; derive an alternative scoring dimension; or rank features in a way not present in the authoritative `feature_scores` data.

Must not appear: a synthesis statement that merely concatenates eleven feature one-liners; any numeric value the narrative computed itself.

---

## 8. Score and Confidence Language Rules

A cross-cutting section governing how narrative text discusses scores anywhere in the report.

### 8.1 Score ≠ Confidence

A high score does not imply high confidence; a lower score does not imply low confidence — two independent dimensions, never merged into a single implied judgment. This is the content-layer counterpart to the design spec's monochrome Confidence Indicator glyph (§1.6 there), which was deliberately built to be visually incapable of implying a score-quality color-code.

### 8.2 Missing Score ≠ Zero

Where a feature's score is null, the narrative must never render or imply "0," "zero score," "poor score," "failed score," or "bad result." Instead it uses non-numeric, non-judgmental language appropriate to which of the two non-scored states applies (§8.3).

### 8.3 The Three States, Narrative Treatment

| State | Narrative must communicate | Narrative must NOT communicate |
|---|---|---|
| **A. Scorable with numeric score** | The score, paired with its confidence (where shown), plus qualitative interpretation | An implied second, unstated score |
| **B. Structurally non-scorable** | This feature has no validated numeric methodology at all — a methodology-level, not per-analysis, fact | An implied numeric evaluation of any kind; never read as "this feature failed to score" |
| **C. Scorable, insufficient evidence** | This analysis's evidence was not sufficient to responsibly compute a score this time — distinct wording from state B | Must not be conflated with state B; must not imply the user did anything wrong |

🔴 Exact wording for states B and C remains open (see §21) — this document requires only that the two states are distinguishable from each other and from state A.

### 8.4 Content-Generation Rules

Confidence, where shown, is always a qualitative label paired with the Confidence Indicator glyph, never a numeric percentage. A score is never described using beauty/attractiveness language.

---

## 9. Multi-Pose Evidence Overview Content

### 9.1 Purpose

Establishes, once, that the analysis is grounded in seven validated original images, before the reader encounters feature-specific subsets of that evidence — matching the design spec's hero-plus-strip gallery (§7.1 there).

### 9.2 The Seven Poses (fixed, unchanged)

Front Face, Left Profile, Right Profile, Left 45°, Right 45°, Smile, Top of Head. No pose is added, removed, or renamed here.

### 9.3 Required Content

A short introduction explaining that the seven images together form the evidence base; pose labels/captions naming each; an optional short explanation that different views contribute different observations (e.g., profile views add projection information not visible from the front).

### 9.4 Content-Generation Rules

Do not generate a long, independent analysis for every pose — the seven images form one combined evidence set, not seven mini-reports. Avoid formulaic per-pose narration ("Front image shows... Left image shows...") unless a specific observation is materially relevant to a specific feature, in which case it belongs in that feature's section (§13), not here. This overview contains only original-evidence captions — no derived or generated-content narration belongs here (§12).

---

## 10. Evidence Category Content

Extending the design spec's three visual badge treatments (§9.1 there) to their content responsibilities:

| Category | Content responsibility |
|---|---|
| **A. Original Evidence** | A short, consistent caption identifying the pose; never described as anything other than an original photograph |
| **B. Derived Evidence** | A short caption identifying it as a crop or annotation, always traceable to its source pose — never presented as a new, independent finding separate from the original it derives from |
| **C. AI-Generated Visualization** | Caption content reinforcing what the design spec's full-width band already signals visually — AI-generated, simulated, illustrative, never described in terms that could be mistaken for measured evidence |

**The core content rule:** narrative and captions must never describe an AI-generated visualization as measured evidence, and a derived crop or annotation must always remain traceable to its original in the accompanying text. Category C content must never use medical/surgical/clinical framing (§16.4).

---

## 11. Eleven Feature Sections — Reusable Content Template

### 11.1 The Eleven Feature Areas (fixed, unchanged)

Hair, Brows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears.

### 11.2 Reusable Structure

| Field | Purpose | Required/Optional |
|---|---|---|
| **A. Feature name/header** | Names the area, carries a priority badge where elevated | Required |
| **B. Feature score/status** | Numeric score + confidence, or one of the two non-numeric states (§8.3) | Required (the state is always present; the numeric value is not guaranteed) |
| **C. Concise summary** | One-line synthesis | Required |
| **D. Detailed findings** | Deeper narrative (§13) | Required |
| **E. Evidence traceability** | The finding is traceable to relevant original pose(s); inline rendering is a design-layer choice, not a content requirement | Required as traceability |
| **F. Multi-angle observations** | What different angles revealed, where relevant | Optional |
| **G. Derived-evidence explanation** | Short caption context for any crop/annotation present | Optional |
| **H. Recommendations** | Actionable, tiered suggestions | Optional — present only where genuinely supported |
| **I. Before/After explanation** | Selective, only for eligible features | Optional |

Always-required: A, B, C, D, E. Conditionally present: F, G, H, I — never fabricated to fill a slot.

### 11.3 Feature-Appropriate Evidence

Reproduces the confirmed pose-to-feature traceability baseline (content responsibility only, no CV constraint):

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

If a pose is unavailable for a specific analysis, it is simply omitted from that section's evidence — never blocking the section from rendering (§20).

### 11.4 Content-Generation Rules

All eleven sections are always present regardless of `scoring_status`, evidence completeness, or Before/After eligibility. Sections need not have identical asset counts or depth — a section with no derived evidence and no Before/After eligibility is still complete.

---

## 12. Feature Summary and Detailed Findings

### 12.1 Feature Summary Rules

Must be concise (one line), neutral, evidence-grounded; must avoid repeating the detailed findings verbatim, beauty/ugliness framing, exaggerated praise or criticism, and medical language. A neutral finding is a valid, complete summary — the summary must not be forced toward a positive or negative conclusion.

### 12.2 Detailed Findings

Should explain, where supported by available evidence: relevant observable characteristics; multi-angle observations where meaningful (§13); relationships/proportions where supported; meaningful asymmetry where supported; how questionnaire context affects interpretation (§14); what evidence supports the observation (§13). Not every subsection needs every observation type — the narrative should be specific to the evidence actually available, not a boilerplate checklist.

---

## 13. Multi-Angle Observations and Evidence Traceability

Uses the pose-to-feature traceability in §11.3; no new mapping is invented here. The narrative may reference frontal, profile, 45-degree, dynamic Smile-pose, or Top-of-Head observations where relevant to a specific feature, and **must synthesize multiple views into one coherent feature-level interpretation** — it does not analyze each pose independently as seven mini-reports. Where views disagree or evidence is uncertain, the narrative does not hide the uncertainty or invent certainty; it uses confidence/evidence-aware language consistent with §8.

Meaningful findings should be traceable to supporting evidence in plain, user-facing language (e.g., conceptually: "most visible in the frontal and 45-degree views"). Raw technical measurement identifiers, storage keys, database IDs, internal measurement/signal names, and confidence internals are never exposed in user-facing prose — traceability language stays at the level a normal user understands.

---

## 14. Questionnaire Personalization

Questionnaire answers may influence emphasis, depth, recommendation relevance, and personalization of report content — never objective CV measurements, any computed score, or a substitute for missing visual evidence. The exact mapping mechanics belong to the future `PHASE2_REPORT_DATA_MAPPING.md`, not this document. The narrative must clearly separate observed facial evidence from user-provided preference/context in substance — a recommendation informed by a questionnaire answer reads as "informed by," never "measured from," that answer.

---

## 15. Recommendation Content

### 15.1 Boundary (unchanged from Phase 1)

Recommendations remain general, cosmetic, appearance-oriented, practical, non-clinical, using the existing three-tier priority system. Allowed categories: hairstyle/grooming, eyebrow styling, facial-hair styling, general skincare presentation, clothing/style considerations where relevant, other non-clinical appearance guidance.

Must not appear: diagnosis, prescription medication advice, surgical planning, treatment plans, disease claims, guaranteed outcomes, or any phased/staged clinical-protocol structure.

### 15.2 Language Register

Prefer tentative phrasing ("may complement," "could consider," "one option is") over absolute or promissory phrasing ("you must," "this will fix," "this guarantees").

### 15.3 No Fabricated Filler

The narrative must never invent a recommendation merely because the feature template's recommendation slot exists. Where no meaningful, evidence-supported recommendation is appropriate, the section simply has no recommendation content — the correct response to thin evidence is reduced specificity or an absent recommendation, never generic filler.

### 15.4 Recommendation Certainty Is Not Scoring Confidence

No recommendation-level confidence/certainty concept is introduced here. A feature's scoring confidence describes the reliability of its numeric score — it must not be silently reused as the confidence behind a recommendation for that feature. The narrative layer does not calculate or infer a recommendation-confidence value.

---

## 16. Before/After Content

### 16.1 Selectivity

Not assumed for every feature — only for features in `before_after_available_features`. A feature with no eligible cosmetic recommendation simply has no Before/After content, not a "not applicable" placeholder; the rest of the section's analysis and score remain complete regardless.

### 16.2 States and Content

| State | Required content |
|---|---|
| Not eligible | No content block at all |
| Pending/generating | A short in-progress note; rest of the section unaffected |
| Generated | Full explanatory content (§16.3) |
| Failed | A short, isolated note that the visualization could not be generated |

### 16.3 Generated-State Content

**Before:** identifies the original evidence already established for that feature (reused, not new). **After:** clearly identifies the image as an AI-generated simulation, explains what cosmetic/styling recommendation is being illustrated, states that it is illustrative, and does not promise a real-world outcome.

### 16.4 Must Never Imply

A medical result, a surgical result, a guaranteed transformation, or a predicted treatment outcome. If generation fails, content communicates only that the optional visualization could not be generated — never "analysis failed." The base report and that feature's written analysis remain fully valid.

---

## 17. Closing Summary

Preserves the four-category structure: Key Takeaways, Strengths, Areas for Improvement, Next Steps. May use authoritative scoring results as one signal informing which items surface — never a new ranking formula invented by the narrative layer. Avoid language like "Your worst features are..." or "Lowest beauty features..."; use neutral framing like "Areas worth focusing on..." or "Features with the most practical opportunities...". Every Next Steps item traces back to a recommendation already shown earlier in the report — this section never introduces new findings.

---

## 18. Content Quality Rules

Content should be clear, specific, concise but informative, evidence-grounded, professional, calm, respectful, non-judgmental, and understandable to a normal user. Avoid repetitive boilerplate, excessive technical terminology, vague filler, unsupported certainty, exaggerated praise or criticism, attractiveness/beauty ranking, clinical terminology, and deterministic promises. Avoid repeating the same observation verbatim across summary, detailed findings, recommendation, and Closing Summary unless repetition materially improves understanding (e.g., a Priority-tier item deliberately re-surfaced in Next Steps).

---

## 19. Hallucination and Evidence Safety Rules

**The narrative layer must not invent:** measurements, scores, confidence, asymmetry, proportions, pose observations, questionnaire answers, visual evidence, recommendation eligibility, or Before/After availability.

**Governing principle: if evidence is missing, say less.** The narrative must not compensate for missing evidence by inventing plausible-sounding content. Where authoritative structured data indicates a feature is unavailable, insufficient, or uncertain, the narrative preserves that state rather than smoothing over it. This is a hard rule with no exception for narrative quality or reader engagement.

**Score/narrative consistency:** the narrative must avoid contradictions — calling a relatively balanced feature severely problematic, using absolute certainty where confidence is low, or implying a numeric evaluation for a structurally non-scorable feature. Where confidence is lower, narrative certainty must be correspondingly more restrained.

---

## 20. Required vs. Optional Content Matrix

| Content element | Required/Optional | Fallback behavior |
|---|---|---|
| Overall score | Required where scoring exists | Interpretation sentence stands alone if absent (legacy) |
| Overall confidence | Conditionally required (🔴 pending) | Omitted entirely if confidence display is rejected |
| Chart context | Required where chart is shown | No accompanying text needed if chart doesn't render (legacy) |
| Seven-pose overview | Required | Original single-photo presentation used instead for legacy reports |
| Each feature section (×11) | Required | N/A — always present |
| Feature score/status | Required (state always present) | Non-numeric state shown per §8.3 |
| Feature confidence | Conditionally required, only alongside a score | Omitted where score is null |
| Original evidence | Required at the evidence-model level | Inline per-section rendering is a design-layer choice |
| Derived crop/annotation | Optional | Simply omitted, no placeholder |
| Recommendation | Optional | Section remains complete without one |
| Before/After | Optional, selective | No block shown, not "not applicable" |
| Closing summary | Required | N/A |
| Disclaimer | Required | N/A — never omitted or shortened |

---

## 21. Open Content Decisions

Carried forward, not resolved here:

### 🔴 Open / require product, legal, or upstream-spec resolution
1. Final score scale (0–100 assumed).
2. Confidence-level display wording, and whether confidence is user-facing at all.
3. Wording for the structurally-non-scorable state.
4. Wording for the insufficient-evidence state.
5. Exact evidence-category badge copy.
6. Pre-payment visual-evidence visibility — this document follows the design spec's conservative posture.
7. Exact Before/After disclosure copy beyond the substance required in §16.3–§16.4.

### 🔵 Proposed / optional, not required unless authoritatively confirmed
8. Recommendation-level confidence/certainty indicator — not introduced by this document (§15.4).
9. Inline original-image rendering per feature section — a design-layer presentation choice, not a content requirement.

None of the above reopens an already-confirmed decision — the eleven feature areas, the seven poses, the questionnaire, score meaning, payment-visibility boundaries, and the non-clinical recommendation boundary all remain fixed.

---

## 22. Relationship to Companion Documents

```
PHASE2_REPORT_DESIGN_SPEC.md    = visual/UX presentation, Meridian token system
PHASE2_REPORT_TEMPLATE.md       = content/narrative structure                    (this document)
PHASE2_REPORT_DATA_MAPPING.md   = exact source/field mapping                     (future)
PHASE2_SCORING_SPEC.md          = deterministic scoring methodology
PHASE2_API_SPEC.md              = external/client-facing data contract
```

These documents must not duplicate each other's responsibilities.

---

## 23. Final Validation

- [x] Exactly 11 feature areas remain.
- [x] Exactly 7 poses remain.
- [x] Questionnaire remains unchanged.
- [x] All feature sections remain present, always.
- [x] Score ≠ confidence, throughout.
- [x] Score:null ≠ 0, throughout.
- [x] The narrative layer never calculates scores.
- [x] The chart caption never calculates scores.
- [x] No fabricated measurements or evidence.
- [x] Evidence traceability is mandatory; inline image rendering is not incorrectly made mandatory.
- [x] No beauty/attractiveness scoring or framing.
- [x] Recommendations remain general/cosmetic, never fabricated as filler.
- [x] Recommendation certainty is not derived from scoring confidence.
- [x] No medical/clinical/surgical framing anywhere, including Before/After.
- [x] Before/After remains selective; generated images remain clearly labelled as simulated.
- [x] A Before/After failure never fails the report.
- [x] Derived evidence remains optional, never a precondition for a complete section.
- [x] Original/derived/generated evidence remain content-distinct.
- [x] Legacy Phase 1 reports remain content-compatible.
- [x] No implementation detail or API/database schema has been introduced.

---

*This document is a content/narrative-structure specification only. It does not implement report generation, PDF generation, frontend components, or application code, and does not modify any database, API, architecture, scoring, or Phase 1 report document, nor `PHASE2_REPORT_DESIGN_SPEC.md`. It is subordinate in authority to `PHASE2_REQUIREMENTS_ANALYSIS.md`, `PHASE2_BRD.md`, `PHASE2_PRD.md`, `PHASE2_SCORING_SPEC.md`, `PHASE2_ARCHITECTURE.md`, `PHASE2_DATABASE.md`, `PHASE2_API_SPEC.md`, and `PHASE2_REPORT_DESIGN_SPEC.md`.*