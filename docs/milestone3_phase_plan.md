# Milestone 3 — Phase Plan

**Source of truth:** [`milestone3_requirements.md`](./milestone3_requirements.md) (the detailed requirements this plan sequences), itself subordinate to [`client_requirements.md`](./client_requirements.md). This document does the same job for Milestone 3 that [`milestone2_phase_plan.md`](./milestone2_phase_plan.md) did for Milestone 2 — it continues that document's Implementation Phase numbering, not client delivery Phase numbering (see the naming-disambiguation note repeated in every phase-plan document in this project).

**Naming disambiguation:** "Milestone 3" is **not yet a numbered client delivery phase** — `client_requirements.md` §2.2 has no "Phase 3" entry. This plan sequences the delivery team's own `[Recommendation]`-labeled proposal from `milestone3_requirements.md`; treat every phase below as provisional until that document's Open Items (`OI-1`–`OI-4`) are resolved. The **Implementation Phases** below continue numbering as **14–19**.

**Status:** Draft roadmap. Nothing in this plan is implemented. Per-module detail plans (`D:\zzz\<module>\plans.md`) are created only once a module's implementation actually starts.

**Version:** 1.0 (2026-09-17).

---

## Phase Overview & Module Map

| Implementation Phase | Name | Module(s) | `plans.md` location (once started) |
|---|---|---|---|
| 14 | Deepened Feature Metrics | `metrics-expansion` | `D:\zzz\metrics-expansion\plans.md` |
| 15 | Recommendation-Level Visual Previews | `recommendation-visuals` | `D:\zzz\recommendation-visuals\plans.md` |
| 16 | Enriched Treatment Protocol | `protocol-enrichment` | `D:\zzz\protocol-enrichment\plans.md` |
| 17 | ~~Progress Tracking Dashboard~~ **REMOVED 2026-09-18** | ~~`progress-tracking`~~ | n/a — reverted, not built |
| 18 | Care Team Support Channel | `support-channel` | `D:\zzz\support-channel\plans.md` |
| 19 | Marketing Landing Page Enrichment | `marketing-landing` | `D:\zzz\marketing-landing\plans.md` |

**Dependency chain:**

```
Milestone 2 (Phases 10-13, complete)
        │
        ├──► Phase 14 (Deepened Metrics)         ── extends FR-018's analysis engine
        │
        ├──► Phase 15 (Recommendation Visuals)    ── reuses Phase 11's Visual Asset infra
        │        depends loosely on Phase 14 (more named metrics → more
        │        candidate recommendations to preview)
        │
        ├──► Phase 16 (Protocol Enrichment)       ── independent; extends the existing
        │                                             Protocol/Treatment Protocol panel
        │
        ├──► Phase 17 (Progress Tracking)         ── BLOCKED on OI-1 sign-off
        │        (milestone3_requirements.md §5) — reopens the "one report
        │        per user" decision; highest effort/risk item in this plan
        │
        ├──► Phase 18 (Care Team Channel)         ── independent, no vendor/data blocker
        │
        └──► Phase 19 (Marketing Landing)         ── independent, content-only,
                                                        can run in parallel with anything
```

Suggested default order: **16 → 14 → 15 → 18 → 19 → 17**, i.e. do the independent, lower-risk, high-value items first (Protocol enrichment is pure data-model+UI, no new AI cost; deepened metrics extends existing CV work; recommendation visuals follow naturally once there are more named recommendations to illustrate), and put Progress Tracking last since it is gated on `OI-1` sign-off and is the only item that touches a previously "Resolved" architectural decision. Phases 18/19 have no dependencies and can be picked up by a different contributor at any point in that sequence.

---

## Phase 14 — Deepened Feature Metrics

**Objective:** Close part of the gap toward the reference site's ~160-assessment depth (`milestone3_requirements.md` §2.2) by adding more named sub-metrics per feature to the existing Features Analysis pages, per `FR-023`.

- **Scope:** Extend `facial_measurement_service.py` with additional per-feature landmark-derived ratios/classifications beyond what `FR-018` already computes; extend `report_assembly_service.py`'s per-feature payload to carry the new named metrics; extend the existing Features Analysis metric-card / "All \[Feature\] Metrics" table UI (already built for `FR-018`) to render more rows — this is additive to an existing UI pattern, not a new one.
- **Modules/features included:** `metrics-expansion`.
- **Functional requirements:** `FR-023`.
- **Technical requirements:** Same 478-point MediaPipe/OpenCV mesh already extracted (`NFR-007`) — no new CV library expected for geometry-derivable metrics (most Eyebrows/Eyes/Nose/Jaw/Cheek/Chin sub-assessments in §2.2's table). Skin- and Smile-adjacent sub-assessments that need pixel/texture analysis rather than landmark geometry (e.g. hyperpigmentation, pore visibility, tooth color) may need a scoped decision on whether to compute them from CV or continue relying on the AI narrative's visual read (current Hair/Neck posture, `phase-wise-requirements.md`) — do not silently fabricate a numeric score for a sub-assessment with no real basis.
- **Dependencies:** Milestone 2 Phase 10 (`report-enrichment`) — extends its data shape, does not replace it.
- **API requirements:** Extends the existing `GET /reports/{id}` response (more fields per feature), no new endpoint.
- **Database requirements:** Extends the existing per-feature JSONB metrics fields (`docs/database-design.md` §4's "favor JSONB while the shape is still moving" convention) — additive, no migration risk to existing data.
- **UI/UX requirements:** More metric rows in an already-built table/card pattern; watch information density — a 2×2 card grid that grows to 10+ items per feature needs a layout decision (e.g. collapsible groups), not just more rows jammed into the current card.
- **Security considerations:** None beyond Phase 10's existing posture.
- **Testing requirements:** Unit tests per new measurement function, same pattern as Phase 10's; a regression test confirming existing `FR-018` fields are unchanged (additive-only).
- **Acceptance criteria:** Each of the 11 features shows a materially deeper metric set than today, sourced from real landmark geometry (or explicitly flagged as AI-narrative-derived where no CV basis exists) — not a padded/fabricated list.
- **Prerequisites:** None blocking.
- **Expected deliverables:** Expanded per-feature metrics in the analysis engine, report payload, and UI; `D:\zzz\metrics-expansion\plans.md` executed.
- **Potential risks:** Scope creep — QOVES' 160+ count is a marketing framing, not a target to hit exactly; risk of chasing a specific number instead of shipping metrics that are actually measurable and meaningful. Cap scope at what's genuinely landmark-derivable per pass.
- **Open questions:** Which specific sub-assessments to add first — recommend prioritizing Eyes/Nose/Jaw (richest geometric basis) over Skin/Smile (need pixel-level or AI-narrative approaches) for the first pass.

## Phase 15 — Recommendation-Level Visual Previews

**Objective:** Generate a small before/after preview **per individual recommendation** (not per feature) with Category/Risk-Level/Product-or-method tags, per `FR-024`.

- **Scope:** For each recommendation line item already produced by the AI narrative/protocol content, generate one small AI before/after image plus three metadata fields (Category, Risk Level, linked product/method name); a UI component to render it inline with the recommendation text (distinct from `FR-022`'s one-per-feature hero image).
- **Modules/features included:** `recommendation-visuals`.
- **Functional requirements:** `FR-024`.
- **Technical requirements:** Reuses `ASM-011`'s Google Gemini 2.5 Flash Image integration and the `Visual Asset` entity from Milestone 2 Phase 11 — no new vendor decision. Category/Risk-Level tagging is a new small classification step, likely a structured-output addition to the existing AI narrative call rather than a separate model.
- **Dependencies:** Milestone 2 Phase 11's shared image-gen infrastructure; loosely benefits from Phase 14 (more named metrics → more specific, illustratable recommendations) but does not hard-block on it.
- **API requirements:** Extends the existing report/recommendation payload with an image reference + 3 metadata fields per recommendation line item.
- **Database requirements:** Reuses the `Visual Asset` table (Phase 11), adding a foreign key from a recommendation line item where one doesn't already exist; may need a new `Recommendation` entity if recommendations are today just narrative text with no discrete row per item — check `report_assembly_service.py`'s current data shape before assuming one exists.
- **UI/UX requirements:** Compact before/after treatment (thumbnail-scale, not full-width like `FR-022`'s per-feature hero image) so a feature page with many recommendations doesn't become a wall of large images; Risk Level should use a consistent color/badge convention across the app.
- **Security considerations:** Same cost/vendor-boundary posture as Phase 11 (`BR-006` — mockable in tests, never a real API call in CI). **Volume risk:** if a report has, say, 5+ recommendations per feature × 11 features, this could multiply the existing "24 generations per report" figure (`milestone2_requirements.md` `OI-2`) substantially — get a per-report generation-count cap decided before implementation, not after a cost surprise.
- **Testing requirements:** Generation mocked in automated tests; a test asserting the per-report generation count stays under whatever cap is decided.
- **Acceptance criteria:** A sample of recommendations across multiple features each show a distinct before/after preview with correct Category/Risk/product tags; total generations per report stay within the agreed cap.
- **Prerequisites:** A decision on the per-report generation cap (cost control) before implementation starts.
- **Expected deliverables:** Per-recommendation visual previews; `D:\zzz\recommendation-visuals\plans.md` executed.
- **Potential risks:** AI image-generation cost is the dominant risk here, more than any other item in this plan — recommend a hard cap (e.g. top N recommendations per report get a visual, not every single one) rather than uncapped generation.
- **Open questions:** Exact generation cap per report — not yet decided, see Security considerations above.

## Phase 16 — Enriched Treatment Protocol

**Objective:** Add cost, cadence, time-to-effect, and difficulty fields to every protocol/recommendation line item, per `FR-025`.

- **Scope:** Extend the Protocol data model (wherever recommendation line items currently live — Home Overview's Treatment Protocol panel and the Report page's own Protocol section) with four new structured fields; extend the AI narrative-generation prompt to produce them per item; extend both UI surfaces to render them (e.g. a small metadata row under each bullet: cost · cadence · time-to-effect · difficulty badge).
- **Modules/features included:** `protocol-enrichment`.
- **Functional requirements:** `FR-025`.
- **Technical requirements:** No new CV or AI vendor — this is a prompt/schema change to the existing narrative-generation call (`ASM-006`'s provider pattern) asking for structured fields per recommendation instead of prose-only bullets.
- **Dependencies:** Milestone 1 Phase 5 (report generation) and Milestone 2 Phase 10 (the Protocol panel/section this extends). No dependency on Phases 14/15/17.
- **API requirements:** Extends the existing report payload's protocol/recommendation shape with 4 new fields per item, no new endpoint.
- **Database requirements:** Extends the existing JSONB protocol/recommendation field(s) — additive.
- **UI/UX requirements:** Must stay within the Meridian design token system; cost/cadence/difficulty should read as scannable metadata (badges/small text), not compete visually with the recommendation's own headline text.
- **Security considerations:** None beyond existing narrative-generation posture (`docs/security.md` §7).
- **Testing requirements:** A test asserting every protocol line item in a generated report carries all 4 new fields (non-null) — treat a missing field as a generation-quality regression, not an acceptable gap.
- **Acceptance criteria:** Both the Home Overview Treatment Protocol panel and the Report page's Protocol section show cost/cadence/time-to-effect/difficulty for every recommendation, for a real generated report.
- **Prerequisites:** None blocking. This is the lowest-risk, most self-contained phase in this plan — good candidate to build first.
- **Expected deliverables:** Enriched protocol data + UI on both surfaces; `D:\zzz\protocol-enrichment\plans.md` executed.
- **Potential risks:** Cost estimates in AI-generated text carry real informational-accuracy risk (a wrong "$25" claim is a small credibility problem, same class of concern as `FR-012`'s existing "never prescriptive" framing) — consider ranges/approximate language rather than exact prices, and keep the existing "informational only, consult a professional" framing attached.
- **Open questions:** Whether cost estimates should be region/currency-aware (this project has no stated target market currency beyond what Stripe already handles) — recommend a simple USD-range default for v1, flag as a follow-up otherwise.

## Phase 17 — Progress Tracking Dashboard — **REMOVED (2026-09-18, client decision)**

**Status:** Implemented once (2026-09-17: re-analysis payment gating, `payment_id` linkage, `/progress` dashboard), then **fully removed at the client's explicit request the next day** ("I dont need the progress functionality remove it"). All code, the DB migration, and the module plan (`D:\zzz\progress-tracking\plans.md`) were reverted/deleted. `FR-026` is no longer in scope for this build. Kept here for traceability, per this project's own convention (see `milestone2_requirements.md`'s `OI-*` precedent) rather than silently deleting the record.

**Objective (historical, no longer pursued):** Let a user re-analyze at a later date and see their key biometric scores trended over time, per `FR-026`. **This phase is blocked on `OI-1` sign-off** (`milestone3_requirements.md` §5) before implementation starts.

- **Scope:** Service-layer change to allow more than one `FacialAnalysisResult`/`Report` per user (schema already anticipates this per `database-design.md` §5's own note); a new "re-analyze" entry point (new photo upload, gated the same way the first analysis is — payment/entitlement model TBD, `OI-1`); a new Progress dashboard screen plotting Symmetry/Proportionality/Averageness/Dimorphism/Visual-Age scores (reusing `FR-018`'s existing Facial Assessments scores, not new metrics) across all of a user's analyses over time; **no projected "with/without protocol" line in v1** (`OI-2` — ship observed data only).
- **Modules/features included:** `progress-tracking`.
- **Functional requirements:** `FR-026`.
- **Technical requirements:** No new CV/AI vendor — reuses the existing analysis pipeline per re-analysis run. The real work is data-model and entitlement logic, not new measurement science.
- **Dependencies:** `OI-1` (multiple-analyses decision) — **blocking, not sequencing-only**, unlike this plan's other cross-phase dependencies. Also depends on Milestone 1 Phase 6 (payment — re-analysis entitlement likely interacts with it) and Phase 7 (dashboard, which this extends).
- **API requirements:** New endpoint(s) to trigger a re-analysis and to fetch a user's score history, e.g. `POST /analyses` (repeatable) and `GET /users/me/progress` — not yet specified in `docs/api-specification.md`; `GET /reports/{id}` semantics need revisiting once "0 or 1 report" (`api-specification.md` line "Multiple reports per user | Resolved — one per user") is no longer true.
- **Database requirements:** Remove or relax the get-or-create one-report-per-user constraint in `report_service.py`; add whatever indexing supports "all of a user's reports, ordered by date" queries efficiently. This is the one item in this entire Milestone 3 plan that changes an existing, already-shipped service's behavior rather than purely adding new surface — treat it with the same care as a data-migration-bearing change, including a rollback plan.
- **UI/UX requirements:** A new dashboard chart component (multi-series line/area chart across analysis dates); an explicit "no projection shown yet" empty state rather than a fake flat line, consistent with this project's "never silently invent data" convention.
- **Security considerations:** Re-analysis must remain scoped per-user (same posture as every other per-user resource in this project); consider rate-limiting re-analysis requests (cost control — each re-analysis re-runs the full CV+AI pipeline, real compute/API cost per `BR-006`).
- **Testing requirements:** A regression test confirming existing single-analysis users are unaffected by the schema/service change; a new test confirming a second analysis for the same user succeeds and both are retrievable; an entitlement test once `OI-1`'s payment model is decided.
- **Acceptance criteria:** A user can trigger a second (and further) analysis, and see their tracked scores plotted across all analyses to date, with no fabricated projection line.
- **Prerequisites:** **`OI-1` sign-off (blocking)** — do not start implementation before this is resolved. `OI-2` (no projection line in v1) should also be explicitly confirmed, not just assumed from this document.
- **Expected deliverables:** Multi-analysis support + Progress dashboard; `D:\zzz\progress-tracking\plans.md` executed.
- **Potential risks:** This is the highest-risk item in the plan — it touches a previously "Resolved" architectural decision (`database-design.md` §5), has an undecided payment/entitlement model (`OI-1`), and re-runs the full (costly) analysis pipeline per use. Recommend building this last in the sequence, after the lower-risk Phases 14/16/18/19 establish momentum.
- **Open questions:** `OI-1` (multi-analysis + entitlement model) and `OI-2` (projection modeling) — both blocking or near-blocking, see `milestone3_requirements.md` §5.

## Phase 18 — Care Team Support Channel

**Objective:** Add a clearly human-staffed support entry point, distinct from the AI Beauty Assistant, per `FR-027`.

- **Scope:** A "Contact your care team" action reachable from the report/chat/settings surfaces, opening a simple support-request form (subject, message, auto-attached report ID/user context) that emails/tickets to the project's existing support channel — no live-chat infrastructure in v1 (`OI-3`).
- **Modules/features included:** `support-channel`.
- **Functional requirements:** `FR-027`.
- **Technical requirements:** Likely reuses an existing transactional-email path if one exists in this codebase, or a simple outbound email/webhook — no new vendor decision expected beyond confirming where submissions should land (`OI-3`).
- **Dependencies:** None beyond a logged-in user context (Milestone 1 Phase 1 auth).
- **API requirements:** New small endpoint, e.g. `POST /support/requests`.
- **Database requirements:** A simple `SupportRequest` record (or, if volume is low, no persistence at all — just relay to email) — decide based on `OI-3`'s staffing-model answer.
- **UI/UX requirements:** Must be visually and behaviorally distinct from the AI Beauty Assistant chat (`FR-019`) — e.g. a labeled "Contact a person" affordance, not styled as another chat bubble thread, so users are never confused about whether they're talking to a model or a human (`FR-027`'s own requirement).
- **Security considerations:** Standard input validation/sanitization on the free-text fields (this is a new user-input surface reaching email/storage); rate-limit submissions to prevent abuse.
- **Testing requirements:** A test confirming a submitted request is delivered/stored correctly and scoped to the submitting user.
- **Acceptance criteria:** A user can submit a support request and it reaches wherever `OI-3` decides it should land; the entry point is clearly labeled as human support.
- **Prerequisites:** `OI-3` (staffing/routing decision) should be answered before building the delivery side, though the UI entry point can be built in parallel.
- **Expected deliverables:** Working support-request flow; `D:\zzz\support-channel\plans.md` executed.
- **Potential risks:** Low — this is a small, self-contained feature. Main risk is setting an implicit response-time expectation the team can't actually staff; keep copy honest (e.g. "we'll respond within X business days") only once that commitment is real.
- **Open questions:** `OI-3` — see `milestone3_requirements.md` §5.

## Phase 19 — Marketing Landing Page Enrichment

**Objective:** Add a social-proof/credibility layer to FaceIQ's own public marketing page, per `FR-028`.

- **Scope:** A benefits/"how it works" section in FaceIQ's own voice; a testimonials section (populated only once real FaceIQ testimonials exist — ship the component with an empty state or placeholder-marked content until then, never fabricated quotes); a press/media-mentions strip (same real-content-only rule).
- **Modules/features included:** `marketing-landing`.
- **Functional requirements:** `FR-028`.
- **Technical requirements:** None — content/UI only, no backend surface, no new data model.
- **Dependencies:** None. Can run fully in parallel with every other phase in this plan.
- **API requirements:** None.
- **Database requirements:** None (or a trivial `Testimonial` content table if the team wants these editable without a redeploy — a CMS-lite decision, not required).
- **UI/UX requirements:** Must match the Meridian design system and the project's premium-UI bar (`NFR-011`/`BC-005`'s quality standard) — this is public-facing, first-impression surface, held to the same bar as everything else, not a quick throwaway section.
- **Security considerations:** None.
- **Testing requirements:** Standard visual/regression coverage; no new business-logic tests needed since there's no new logic.
- **Acceptance criteria:** The public landing page has a credible, non-fabricated social-proof section; if no real content exists yet, the section is either omitted or clearly marked as forthcoming rather than shipped with placeholder text presented as real.
- **Prerequisites:** Real testimonials/press mentions, if the intent is to launch this fully populated — otherwise ship the structural components empty/deferred.
- **Expected deliverables:** Enriched public landing page; `D:\zzz\marketing-landing\plans.md` executed.
- **Potential risks:** Lowest risk item in this plan. Only real risk is shipping fabricated social proof, which this document explicitly rules out (§4 of `milestone3_requirements.md`).
- **Open questions:** None blocking — purely a matter of when real content is available.

---

## Related Documents

- [`milestone3_requirements.md`](./milestone3_requirements.md) — the requirements this plan sequences.
- [`milestone2_phase_plan.md`](./milestone2_phase_plan.md) — the immediately preceding phase plan; Phases 14–19 above continue its numbering.
- [`client_requirements.md`](./client_requirements.md) — governing source of truth (Milestone 3 is not yet folded into it).
