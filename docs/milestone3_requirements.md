# Milestone 3 Requirements — AI Facial Analysis Platform

**Source of truth:** [`client_requirements.md`](./client_requirements.md) remains the single project source of truth. This document is a **subordinate, detailed addendum** — the same relationship [`milestone2_requirements.md`](./milestone2_requirements.md) has to it — recording what the **QOVES.com live reference website** shows, so Milestone 3 implementation has a literal spec to build against.

**Status:** Draft — feature set proposed by the delivery team from the reference site, pending confirmation. Nothing in this document has been implemented yet.

**Version:** 1.0 (2026-09-17).

**"Milestone 3" naming:** continues the naming pattern `milestone2_requirements.md` §"Milestone 2 naming" established — Milestone 1 = client delivery Phase 1, Milestone 2 = client delivery Phase 2 (`client_requirements.md` §2.2). **Milestone 3 has no corresponding numbered phase in `client_requirements.md`** — it is not yet client-scoped. Every requirement below is therefore labeled **[Recommendation]**, not **[Client-stated]** (contrast with Milestone 2, where the client supplied the reference material directly). This document exists so the delivery team's own proposal is written down precisely enough to be reviewed, edited, and signed off, per `client_requirements.md`'s own rule (§ "Do not invent requirements... anything not explicitly stated by the client is labeled").

---

## 1. Source Material

Reviewed live on 2026-09-17: **`https://www.qoves.com/`** (marketing/product site for QOVES — the same reference business already named in this project's origin documents, `BC-001`/`BC-002`/`BR-008`: *"an AI-driven facial aesthetics analysis platform, conceptually similar to Qoves.com."* Qoves' own onboarding flow and sample report already informed Milestone 1's `FR-003`–`FR-005`/`FR-009`/`FR-012`). Milestone 3 goes back to the same reference for its **current, public-facing product** — the site has evidently grown since the Milestone 1 reference material was captured.

**Review method:** the site was fetched and read directly (homepage + its long-scroll marketing sections); no separate "how it works" route exists — content that reads like distinct pages is actually anchored sections on one long homepage. No paid checkout flow, live dashboard, or protocol screen was accessed (that requires an account/payment) — the dashboard/protocol/visualization descriptions below come from the marketing page's own screenshots and captions, not a logged-in walkthrough. **Same posture as every other reference-derived spec in this project:** this is the delivery team's reading of a competitor's public marketing material, not a literal spec, and specific numbers (e.g. "521 facial points," "160+ beauty markers," "450+ methods") are the reference site's own marketing claims — carried here for traceability, not as commitments this project must match exactly.

**Branding note (does not need restating per-requirement below):** QOVES is the reference product's own name/branding. This project's product name remains **FaceIQ** — every requirement below describes *behavior and structure* to draw inspiration from, never literal branding, copy, or unverifiable statistics (e.g. "50,000+ people," the specific academic citations) to reuse. Same posture as `milestone2_requirements.md`'s branding note and `CON-003`.

---

## 2. What the Site Shows — Feature Inventory

### 2.1 Marketing / Acquisition Layer
Hero ("Improve your looks without surgery"), a "Why Glow-Up" section citing attractiveness-outcome research, an "As Seen In" media-logo strip, a medical advisory board (10 named plastic surgeons/dermatologists with credential blurbs), and user testimonials (Trustpilot quotes + content-creator social proof with follower counts). Pure marketing content — no application logic.

### 2.2 The 160+ Assessment Taxonomy
The core differentiator this project doesn't yet fully match: QOVES frames its facial analysis as **160+ individually named beauty assessments**, grouped by feature, each with its own label (not just a metric card with 2–4 attributes, as FaceIQ's current `FR-018` Features Analysis pages have). Categories and counts as shown on the site:

| Feature | Assessment count | Representative named sub-assessments |
|---|---|---|
| General | 8 | First Impression, Facial Masculinity/Femininity, Facial Averageness, Facial Proportions, Facial Symmetry, Perceived Youthfulness, Face Shape |
| Eyebrows | 14 | Brow Shape/Thickness/Position/Lift/Tilt, Start/End Point, Interbrow Distance, Tail Length/Drop |
| Eyes | 26 | Eye Shape/Size/Width/Height, Upper/Lower Eyelid Exposure, Under-Eye Health/Pigmentation/Puffiness/Hollowness, Intercanthal & Interpupillary Distance, Scleral Show/Color, Limbal Ring Visibility, Epicanthic Fold |
| Nose | 17 | Bridge Width/Height/Shape, Tip Definition/Projection/Rotation, Nostril Shape/Flare, Nasofrontal & Nasolabial Angle, Columella/Septum Alignment |
| Lips | 16 | Fullness, Upper/Lower Ratio, Cupid's Bow, Philtrum Shape, Vermilion Definition, Oral Commissure Tilt, Gloss/Hydration |
| Cheeks | 13 | Cheekbone Projection/Shape/Position/Height, Mid-Cheek Fullness, Under-Cheek Hollowing, Cheek-to-Jaw/Eye Balance |
| Jaw | 11 | Jaw Shape (Frontal/Side), Jawline Definition/Length/Contrast, Jaw-to-Face/Cheek Ratio, Flare Symmetry |
| Chin | 8 | Shape, Projection, Width, Height, Contour, Fullness, Dimple, Inclination |
| Smile | 13 | Tooth Show/Color/Alignment, Smile Symmetry/Width, Gum Visibility, Buccal Corridors, Duchenne Activation |
| Neck | 11 | Shape, Submental Fat, Firmness, Taper, Posture, Adam's Apple Visibility |
| Ear | 12 | Shape, Projection, Angle, Helix/Antihelix/Earlobe/Bowl Shape |
| Skin | 20 | Tone/Undertone, Acne & Scarring, Hyperpigmentation, Pore Visibility/Size, Fine Lines/Wrinkles, Redness, Sun Damage, Oiliness |

Note: QOVES' own taxonomy has 12 groups including a separate **Smile** category — FaceIQ's `BR-011` already made the deliberate decision to fold Smile into Lips and keep exactly 11 features (`BR-008`). This document does not reopen that decision; the taxonomy above is a *sub-assessment depth* reference, not a feature-count reference.

Site copy also states every analysis is **"carefully reviewed by our team"** (a human-QA step) and that scoring factors in ethnicity/demographic background, personal style preference, lifestyle (diet/climate/stress/sleep), natural aging trajectory, and regional beauty-standard context.

### 2.3 Transformation Visualization ("See your future you")
Per-recommendation (not per-feature) AI-generated before/after previews, explicitly tagged with metadata on each suggested change — the site's own example: *"Make eyebrows darker — CATEGORY: Cosmetic, RISK LEVEL: Low, Products Recommended: Eyebrow Tinting Kit."* Copy stresses "ethnicity-aware" rendering and that showcased changes are "realistic and achievable without surgery." This is a different grain of AI visual than FaceIQ's existing `FR-020`/`FR-022` (whole-feature or category-level before/after) — QOVES generates one preview **per individual recommended action**, each carrying a category tag, a risk-level tag, and a linked product/method.

### 2.4 Personalized Glow-Up Protocol
A phased recommendation plan (the site shows a female-transformation example: *Phase 1 — Key vitality signals (0–1 month)*, *Phase 2 — Basic facial proportions (1–2 months)*, *Phase 3 — Balancing dimorphism (2–4 months)*). Distinguishing detail versus FaceIQ's current Treatment Protocol panel (`milestone2_home_and_report_spec.md`, Phase 10's Protocol section): **every recommendation line item carries structured metadata** — an estimated cost (e.g. "$25," "$35–55"), a frequency/cadence (e.g. "Nightly," "Daily, 5 min AM," "monthly"), a time-to-effect (e.g. "8+ weeks," "Immediate"), and a difficulty rating (Easy/Medium). FaceIQ's current Protocol content is bullet text with a duration string only — no cost, cadence, or difficulty fields exist in the data model yet.

### 2.5 Progress Tracking Dashboard
A dashboard tracking named biometric scores **over time**, across repeated check-ins/re-analyses, not a single snapshot: Facial Femininity, Averageness, Symmetry, Cheek Activation, Homogeneity, Proportionality, and Visual Age, each shown against an "IDEAL" band and a multi-year axis (the site's own example spans "2024 2025 2026"). A chart contrasts a **projected trend "With QOVES Recommendations" vs. "Without."** This requires the product to support **more than one analysis per user over time** — see §5 `OI-1` below, which flags a direct conflict with this project's existing, already-`Resolved` "one report per user, no re-run" decision (`docs/database-design.md` §5).

### 2.6 Care Team Support
"Ask any questions directly to our care team via chat" — the site frames this as **human** support staff answering questions about a user's own recommendations, distinct from an AI assistant. FaceIQ already has an AI Beauty Assistant (`FR-019`, Milestone 2 Phase 12) that answers report-grounded questions automatically; QOVES' "Care Team" appears to be a **human-staffed** escalation channel layered on top of (not a replacement for) that kind of automated assistant. No implementation detail beyond this one line is visible on the public site.

---

## 3. Functional Requirements — Milestone 3 (`FR-023`–`FR-028`)

Numbered continuing from `milestone2_requirements.md`'s `FR-022`. **All entries below are `[Recommendation]`** (see naming note above) — none are client-stated; all require sign-off before implementation starts (§5).

| ID | Requirement | Source |
|---|---|---|
| **FR-023** | **Deepened per-feature metric taxonomy.** Extend the analysis engine and Features Analysis report pages (`FR-018`) with additional named sub-metrics per feature, closing the gap toward QOVES' ~160-assessment depth (§2.2) — not necessarily the exact same count or names, but materially more than FaceIQ's current 2×2 metric-card pattern per feature. Where a named QOVES sub-metric has no CV/landmark basis today (e.g. several Skin and Smile sub-assessments), it must be flagged rather than fabricated, same posture as `FR-018`'s original scoring caveat (`OI-5` in `milestone2_requirements.md`). | [Recommendation] (from QOVES reference site, 2026-09-17) |
| **FR-024** | **Recommendation-level visual previews.** For each individual recommendation surfaced in a feature's narrative/protocol (not just one image per feature as `FR-022` does today), generate a small before/after preview tagged with a Category (e.g. Cosmetic/Lifestyle/Clinical), a Risk Level (Low/Medium/High), and a linked product or method name (§2.3). Shares the existing Milestone 2 image-generation infrastructure (`ASM-011`, Phase 11's shared `Visual Asset` entity) rather than introducing a second vendor. | [Recommendation] (from QOVES reference site, 2026-09-17) |
| **FR-025** | **Enriched Treatment Protocol data model.** Add structured fields to each protocol/recommendation line item: estimated cost (or cost range), cadence/frequency, time-to-effect, and a difficulty rating (§2.4). Applies to both the Home Overview's "Treatment Protocol" panel and the Report page's own Protocol section (the latter already flagged as an unverified content gap in `milestone2_phase_plan.md` Phase 10). | [Recommendation] (from QOVES reference site, 2026-09-17) |
| ~~**FR-026**~~ | ~~**Progress Tracking Dashboard.**~~ **REMOVED 2026-09-18 — client decision: "I dont need the progress functionality remove it."** Was implemented 2026-09-17 (re-analysis payment gating, `payment_id` linkage, `/progress` dashboard), then fully reverted the next day, including the DB migration. No longer in scope. Original text kept below for traceability only, per this project's own convention of not silently deleting a resolved/superseded requirement: ~~Let a user trigger a **new** analysis from freshly uploaded photos at a later date, and view their named biometric scores (at minimum: Symmetry, Proportionality, Averageness, Dimorphism/Femininity-Masculinity, Visual/Perceived Age — reusing `FR-018`'s existing Facial Assessments scores rather than inventing new ones) plotted across all of their analyses over time, on a dedicated dashboard screen (§2.5). A "with protocol vs. without" projected comparison line is out of scope for the first implementation pass (no ground truth to model a counterfactual against — flag as a follow-on, do not fabricate a trend line) — see `OI-2`. This is the largest and most architecturally significant item in this document — it requires reopening `docs/database-design.md`'s already-`Resolved` "one report per user, no re-run" decision (§5 `OI-1`, blocking).~~ | [Recommendation] (from QOVES reference site, 2026-09-17) — **removed 2026-09-18** |
| **FR-027** | **Care Team / human support channel.** A lightweight, clearly-human-staffed support surface reachable from the report/chat experience (e.g. a "Contact your care team" action that opens a support request form or a mailto/ticket flow), distinct from and additive to the existing AI Beauty Assistant (`FR-019`) — the two must be visually/behaviorally distinguishable so users are never misled about whether they're talking to a person or a model. Actual staffing/response-time commitments are a business/operations decision outside this document's scope — see `OI-3`. | [Recommendation] (from QOVES reference site, 2026-09-17) |
| **FR-028** | **Public marketing landing page enrichment.** Add a social-proof/credibility layer to FaceIQ's own public (pre-login) marketing page: real testimonials (once FaceIQ has actual users to quote — do not fabricate quotes or statistics), a media/press-mentions strip (only once real mentions exist), and a "how it works"/benefits section modeled on QOVES' structure (§2.1) but written in FaceIQ's own voice. Content-only, no new backend surface. Lowest priority of this document's items — marketing copy, not core product functionality. | [Recommendation] (from QOVES reference site, 2026-09-17) |

---

## 4. Explicit Non-Goals (do not build without a separate decision)

- **Do not copy QOVES' specific marketing statistics, testimonial quotes, advisor names, or academic citations** (§2.1) — those are QOVES' own claims/assets, not FaceIQ's. `FR-028` requires real FaceIQ data before shipping any social-proof content.
- **Do not fabricate a "with protocol vs. without" projected trend line** for `FR-026` without a stated modeling approach signed off first (`OI-2`) — an invented projection is a credibility risk the same way an invented score would be.
- **Do not treat this document as reopening `BR-008`/`BR-011`'s exactly-11-features rule** — `FR-023`'s deeper taxonomy stays inside the existing 11 features (Smile content stays folded into Lips).

---

## 5. Open Items Requiring Sign-Off (`OI-*`)

Local to this document, restarting from `OI-1` (same convention `milestone2_requirements.md` used for its own five items — this numbering is per-document, not global).

- **OI-1 — Multiple analyses per user (blocks `FR-026`).** `docs/database-design.md` §5 already resolved (v1.9) that a user has exactly one `FacialAnalysisResult`/`Report`, enforced by `report_service.get_or_create_report`'s get-or-create semantics, explicitly *"a future re-analysis/multiple-reports feature would only need a service-layer change"* — i.e. the schema already anticipated this, but the service-layer and payment-gating logic (re-analysis presumably needs its own payment or plan entitlement — is a re-analysis free, paid again, or plan-included?) do not exist yet and need a product decision, not just an engineering one, before Phase 17 (§ phase plan) starts.
- **OI-2 — Projected/counterfactual trend modeling for `FR-026`.** QOVES shows a "with recommendations" vs. "without" projected line on its progress chart. This project has no basis (no longitudinal outcome data) to model a real counterfactual. Recommend shipping `FR-026` v1 with **actual, observed scores only** (no projected line) and revisiting a projection feature once real repeat-analysis data exists to validate against.
- **OI-3 — Care Team staffing model for `FR-027`.** Whether "Care Team" support is: (a) routed to existing project/support staff via email/ticket, (b) a scheduled feature for a future support hire, or (c) dropped in favor of just the AI assistant, is a staffing/operations decision this document cannot make. Recommend shipping the UI entry point + a simple ticket/email capture first, deferring live-chat infrastructure.
- **OI-4 — Scope and priority ordering.** This document proposes six independent-ish items (`FR-023`–`FR-028`). Recommend confirming priority order before the phase plan's suggested sequencing is treated as final — `FR-026` (Progress Tracking) is the highest-effort, highest-value, and highest-risk item (architecture change); `FR-028` (marketing polish) is the lowest-effort and can slot in anytime, including in parallel by a different contributor.

---

## 6. Related Documents

- [`client_requirements.md`](./client_requirements.md) — governing source of truth; this document's items are proposals, not yet folded into it.
- [`milestone2_requirements.md`](./milestone2_requirements.md) / [`milestone2_phase_plan.md`](./milestone2_phase_plan.md) — the immediately preceding milestone; `FR-024` and `FR-025` extend infrastructure (`ASM-011` image-gen, the Protocol panel) that milestone builds.
- [`milestone3_phase_plan.md`](./milestone3_phase_plan.md) — breaks this document's requirements into implementation phases (continuing Phase 14 onward).
- [`database-design.md`](./database-design.md) §5 — the "one report per user" decision `FR-026`/`OI-1` requires revisiting.
