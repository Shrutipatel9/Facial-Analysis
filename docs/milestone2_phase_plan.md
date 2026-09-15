# Milestone 2 — Phase Plan

**Source of truth:** [`milestone2_requirements.md`](./milestone2_requirements.md) (the detailed requirements this plan sequences), itself subordinate to [`client_requirements.md`](./client_requirements.md). This document does the same job for Milestone 2 that [`phase-wise-requirements.md`](./phase-wise-requirements.md) does for Milestone 1 — it does not replace that document, it continues its numbering.

**Naming disambiguation (same rule as `phase-wise-requirements.md`):** "Milestone 2" = client delivery Phase 2 (`client_requirements.md` §2.2). The **Implementation Phases** below continue that document's 0–9 numbering as **10–13**, entirely inside client delivery Phase 2. Per-module detail plans (`D:\zzz\<module>\plans.md`) are created **only once that module's implementation actually starts** — none exist yet for Milestone 2; this document is the pre-implementation roadmap `client_requirements.md`'s working conventions call for.

**Status:** Draft roadmap. **Phase 10 (Enriched Interactive Report: `FR-018` Facial Assessments + `FR-022` per-feature before/after) is implemented**, including a subsequent PDF-redesign presentation pass. **Home Overview presentation gap (2026-09-14):** the MyFace video’s first post-approval screen (§2.1 / [`milestone2_home_and_report_spec.md`](./milestone2_home_and_report_spec.md)) is not yet the FaceIQ landing — interim code lands on `/report`. Closing that gap is a **presentation/IA pass on existing Phase 10 data**, not a new CV/AI phase. Phase 11 AI Visuals is implemented; Phases 12–13 as below.

**Version:** 1.4 (2026-09-14) — notes Home Overview landing gap + links implementer checklist. Continues 1.3 aging-cadence correction.

---

## Phase Overview & Module Map

| Implementation Phase | Name | Module(s) | `plans.md` location (once started) |
|---|---|---|---|
| 10 | Enriched Interactive Report | `report-enrichment` | `D:\zzz\report-enrichment\plans.md` |
| 11 | AI Visual Features | `ai-visuals-hairstyle`, `ai-visuals-outfit`, `ai-visuals-aging` | `D:\zzz\ai-visuals-hairstyle\plans.md`, `D:\zzz\ai-visuals-outfit\plans.md`, `D:\zzz\ai-visuals-aging\plans.md` |
| 12 | AI Beauty Assistant Chat | `chat-assistant` | `D:\zzz\chat-assistant\plans.md` |
| 13 | Settings & Billing Restructure | `settings-billing` | `D:\zzz\settings-billing\plans.md` |

Phase 11 is split into three modules rather than one — per the project's own "if a phase is long, divide into modules" convention — because hairstyle/outfit/aging are three genuinely separate generation pipelines (different prompt engineering, different input framing, different UI copy) that happen to share one page shell and one underlying image-gen vendor integration, not one feature with three views.

**Dependency chain (revised — Phase 10 and Phase 11 now share a prerequisite):** Phase 10 depends on Milestone 1's Phases 4/5 (analysis engine + report generation — it *extends* both) **and**, as of `FR-022`, on the same image-generation vendor decision (`OI-2`) and shared `Visual Asset`/generation infrastructure Phase 11 builds — whichever of Phase 10 or Phase 11 starts implementation first should build that shared infra once, the other reuses it. Phase 12 and Phase 13 depend only on Milestone 1's Phase 6/7 (payment + dashboard) being complete, which they already are — **12 and 13 have no dependency on 10, 11, or each other**, and can be built in any order or in parallel with everything else. Suggested default order (10 → 11 → 12 → 13) follows the reference video's own screen order, not a hard technical requirement — but 10 and 11 can no longer be treated as fully independent of each other.

```
Milestone 1 (Phases 0-9, complete)
        │
        ├──► Phase 10 (Enriched Report)  ──┐
        │      FR-018 + FR-022             │  share ASM-011 (Gemini 2.5 Flash
        │                                   │  Image) + Visual Asset infra
        ├──► Phase 11 (AI Visuals)      ───┘  (build once, either phase first)
        │      ├─ ai-visuals-hairstyle
        │      ├─ ai-visuals-outfit
        │      └─ ai-visuals-aging
        │
        ├──► Phase 12 (Chat Assistant)      ── independent, no vendor blocker
        │
        └──► Phase 13 (Settings/Billing)    ── independent, no vendor blocker
```

---

## Phase 10 — Enriched Interactive Report

**Status:** Implemented — backend (`FR-018`/`FR-022`) and the `/report` TOC-nav experience are live; PDF redesign reuses the same data. **Still open (presentation):** ship **Home Overview** as post-completion landing per [`milestone2_home_and_report_spec.md`](./milestone2_home_and_report_spec.md) (stats row, before/potential, priority features, protocol panel, harmony block). Do not reintroduce the Milestone 1 “Welcome back” dashboard cards for AI Visuals/Chat (those live in the header nav). Whole-face Potential image and Facial Age remain known gaps (see Phase 10 prerequisites note below).

**Objective:** Extend the existing `/report`-equivalent screen with the "Facial Assessments" category (Dimorphism, Prototypicality, Proportions, Symmetry, Face Shape) and deepen "Features Analysis" with per-feature named-ratio detail cards and raw-metrics tables (`FR-018`), **and** give each of the 11 existing features its own AI-generated before/after image (`FR-022`), per `milestone2_requirements.md` §2.2/§3/§4.

- **Scope:** New CV-computed indices in the analysis engine (masculinity/femininity score per feature, prototypicality score, facial-thirds ratios, symmetry score, face-shape classification); new report-assembly fields to carry them; **one AI-generated before/after image per feature** (`FR-022`, resolves `BR-008`'s 11-feature count staying fixed thanks to `BR-011` folding Smile into Lips), using the shared image-generation infrastructure defined in Phase 11; new frontend sections/components rendering score cards, sliders, a facial-thirds photo overlay, a face-shape wireframe diagram, and the per-feature before/after image — built as extensions to the existing Meridian design system (`docs/report_design_spec.md`), not a new visual system.
- **Modules/features included:** `report-enrichment`. Touches `Backend/app/services/facial_measurement_service.py` (extension, not rewrite), `Backend/app/services/report_assembly_service.py`, and (for `FR-022`) whatever image-generation client Phase 11 establishes, plus `frontend/src/components/report/`.
- **Functional requirements:** `FR-018`, `FR-022`.
- **Technical requirements:** `FR-018`'s indices build on `NFR-007` (MediaPipe/OpenCV) — no new CV library expected, these are new ratios/classifications computed from the same 478-point landmark mesh already extracted. `FR-022` uses `ASM-011`'s Google Gemini 2.5 Flash Image, shared with Phase 11.
- **Dependencies:** Milestone 1 Phase 4 (`facial-analysis-engine`) and Phase 5 (`report-generation`) — `FR-018` extends both. **`FR-022` additionally depends on Phase 11's shared image-gen infrastructure** — whichever of Phase 10/11 starts first builds the shared `Visual Asset` entity + `ASM-011` generation-client wrapper described in Phase 11 below; the other reuses it. (The vendor *choice* itself, `OI-2`, is resolved — this is now an implementation-sequencing dependency, not an open decision.)
- **API requirements:** Extends the existing `GET /reports/{id}` response shape (new fields, including a per-feature image reference for `FR-022`), not a new endpoint family — see `docs/api-specification.md` §7 for the current contract this must stay backward-compatible with.
- **Database requirements:** Extends `Facial Analysis Result` / `Report` (`docs/database-design.md` §2.6/§2.7) with new JSONB fields for the new indices, plus a reference to each feature's generated `Visual Asset` row (shared table, defined once in Phase 11) — same "favor JSONB while the shape is still moving" convention `docs/database-design.md` §4 already establishes, not new tables of its own.
- **UI/UX requirements:** New TOC-nav report layout (left-hand section list driving a scrollable content pane) — a real navigation-pattern change from the current report screen, not just new cards; must stay within the Meridian token system (`docs/report_design_spec.md` §1) and the app-wide toast/confirm-dialog conventions (`BR-009`/`BR-010`). Each feature's existing narrative card gains a before/after image slot.
- **Security considerations:** `FR-018` — none beyond what Phase 5 already covers. `FR-022` — the same cost/vendor-boundary considerations as Phase 11 (`BR-006`, mockable in tests, never a real API call in CI).
- **Testing requirements:** Unit tests for each new measurement function (same pattern as `Backend/tests/unit/test_facial_measurement_service.py`); a regression test asserting the existing 11-feature report shape is unaffected by the new fields (additive-only change); `FR-022`'s image generation mocked in automated tests, same posture as the existing AI narrative call.
- **Acceptance criteria:** A generated report exposes Dimorphism/Prototypicality/Proportions/Symmetry/Face-Shape data for a real analyzed photo set, plus a generated before/after image for each of the 11 features; the existing 11-feature PDF export (`FR-013`) gains the same before/after images and is otherwise unaffected (per `milestone2_requirements.md` §3's revised conclusion).
- **Prerequisites:** None blocking — all five Milestone 2 open items (`OI-1`–`OI-5`) are resolved as of `client_requirements.md` v1.24. `FR-022` implementation should still be sequenced against Phase 11 (build the shared `Visual Asset`/`ASM-011` infra once, in whichever phase starts first). **Known content gap (v1.25):** the source video never actually opens **Face Shape** (a Facial Assessments sub-tab), **Skin** (the 12th Features Analysis page), or the Report page's own **Protocol** presentation — confirmed absent via dense re-sampling, not merely unobserved. Build these three against the confirmed sibling patterns (Face Shape like Prototypicality/Symmetry's single-overview-page shape; Skin like the other 11 Features Analysis pages; Protocol like the Dashboard's fully-confirmed Treatment Protocol panel) as a reasonable best-effort default, but flag them for a follow-up client review rather than treating them as verified — do not present these three as "matches the reference" in any client-facing communication. **Known content gap, round 2 (this session):** a direct page-by-page read of the reference PDF (`MyFace-Protocol-test-1 (3).pdf`) plus fresh Dashboard/Report screenshots surfaced further reference detail not yet built and deliberately deferred this round: named multi-subsections within a feature page (e.g. Hair splitting into "Hair Style/Hair Loss/Hair Health"), a Norwood-style hair-loss chart (Hair has zero CV measurement today — no ground truth to classify from), a line-overlay "Analysis" image on the Cheek page, a whole-face annotated landmark-callout diagram, a "Facial Age" figure, a dual-series (Projected Potential vs. Client Values) radar, and a whole-face AI-generated "Potential" image (today's image generation only ever operates on per-feature crops, never the whole face). Same posture as the v1.25 gap above: flag for a follow-up review, do not build blind, do not present as matching the reference until scoped.
- **Expected deliverables:** Enriched report UI + backend measurement extensions + per-feature before/after imagery; `D:\zzz\report-enrichment\plans.md` executed.
- **Potential risks:** The new `FR-018` scores are first-pass heuristics with no ground truth to validate against (same risk class as `ASM-002`/`ASM-010`) — expect a tuning pass. The new TOC-nav layout is a real information-architecture change; get sign-off on the layout direction before building all five Facial Assessments sub-pages against it. `FR-022`'s output quality against this project's own real uploaded photos is unvalidated (`ASM-011`) — expect a tuning pass once real generations can be reviewed.
- **Open questions:** None blocking.

## Phase 11 — AI Visual Features

**Objective:** Ship the three AI-generated visual preview features (Hairstyle, Outfit, Healthy Aging), all sharing one before/after-with-variations UI pattern and one underlying image-generation vendor integration, per `FR-020`.

**This phase is intentionally split into three modules** (see rationale in the Phase Overview note above). All three share the common shell described below; each module owns its own generation prompts/logic and its own five (or, for aging, N) variation set.

### Shared infrastructure (build once, in whichever of the three modules starts first)
- A new **Visual Asset** data entity (`client_requirements.md` §9 already names this as deferred-to-Phase-2 — activated now): generated image reference, kind (hairstyle/outfit/aging), variation label/metadata, source report/user, generated-at timestamp.
- A new image-generation vendor integration — **Google Gemini 2.5 Flash Image**, per `ASM-011` (resolves `OI-2`) — with the same "swappable via config, not hardcoded to one vendor" posture this project already uses for the AI narrative call (`ASM-006`'s `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL` pattern).
- A shared frontend "variation gallery" component: draggable before/after split-image, 5-thumbnail (or N-card, for aging) selector row, right-hand recommendation detail panel — built once, reused by all three modules' pages.

### Module: `ai-visuals-hairstyle`
- **Scope:** 5 AI-generated hairstyle variations on the user's own front photo, each with a name, maintenance/layers/parting/vibe attributes, and an explanation sentence.
- **Functional requirements:** `FR-020`(a).
- **Dependencies:** Shared infrastructure above; the user's own validated front photo (Milestone 1 Phase 3).
- **Acceptance criteria:** 5 distinct, face-preserving hairstyle variations generate successfully for a real uploaded photo; before/after slider and thumbnail switching both work.

### Module: `ai-visuals-outfit`
- **Scope:** 5 AI-generated shoulder-up outfit/styling variations, each with a name, occasion/formality/palette/vibe attributes, and an explanation sentence.
- **Functional requirements:** `FR-020`(b).
- **Dependencies:** Shared infrastructure above.
- **Acceptance criteria:** 5 distinct shoulder-up outfit variations generate successfully; same slider/thumbnail interaction pattern as hairstyle.

### Module: `ai-visuals-aging`
- **Scope:** A stacked age-progression preview, **confirmed cadence (verified via dense video re-sampling, v1.25): 4 cards at non-uniform steps — current/28 (the user's own photo, not generated), +3yr/31, +5yr/33, +10yr/38** (resolves `OI-4`, matching the MyFace reference exactly — corrects an earlier, incompletely-sampled "5 cards, uniform +5-year steps" reading), each of the 3 generated cards carrying a mandatory "educational purpose only, not a forecast" disclaimer footer.
- **Functional requirements:** `FR-020`(c).
- **Dependencies:** Shared infrastructure above.
- **Security/ethics considerations:** This is the most sensitive of the three sub-features (age-progression imagery) — the disclaimer requirement is non-negotiable, matching `FR-004`'s BDD-safety posture; must not imply medical/clinical prediction.
- **Acceptance criteria:** All 4 age-progression cards (current/+3yr/+5yr/+10yr) render correctly, each of the 3 generated cards with the disclaimer visible, not just present in a tooltip.

**Cross-module notes:**
- **API requirements:** New endpoint family, e.g. `POST /ai-visuals/{kind}/generate`, `GET /ai-visuals/{kind}` — listed as Milestone 2 scope but no concrete contract yet in `docs/api-specification.md` §10; this phase specifies it.
- **Database requirements:** New `Visual Asset` table(s) — see shared infrastructure above and `docs/database-design.md` §3.
- **Testing requirements:** Generation calls must be mockable in automated tests, same posture as the existing AI narrative call (`BR-006`, `ai_narrative_service.get_ai_client()`'s monkeypatch pattern) — real image-gen API calls cost real money per `BR-006` and must never run in CI.
- **Potential risks:** Real per-generation cost (`BR-006`) — this phase alone is 13 generations per paying user (5 hairstyle + 5 outfit + 3 aging), and combined with Phase 10's `FR-022` (11 more) the true per-report total is **24 generations**, not the ~12 originally estimated — a materially larger AI spend than the single narrative call Milestone 1 makes; the client has confirmed the vendor with this cost in view (`ASM-011`), but actual per-generation pricing should still be checked before implementation. Face-preserving image generation is failure-prone (identity drift, artifacts) — expect a quality-tuning pass and a fallback/regenerate affordance in the UI.
- **Open questions:** None blocking — `OI-2` (vendor) and `OI-4` (aging cadence) both resolved, see `milestone2_requirements.md` §5.

## Phase 12 — AI Beauty Assistant Chat

**Objective:** Ship a conversational interface where the user asks free-text questions about their own report, grounded in their actual measurements/narrative/questionnaire context, per `FR-019`.

- **Scope:** Chat UI (empty-state suggested prompts, streamed markdown responses, persistent-per-user conversation history), backend chat endpoint that constructs a system/context prompt from the user's own `Report`/`FacialAnalysisResult`/`QuestionnaireResponse` rows, and a hard-enforced refusal behavior for medical/medication/prescription questions.
- **Modules/features included:** `chat-assistant`.
- **Functional requirements:** `FR-019`.
- **Technical requirements:** Reuses the existing AI provider integration pattern (`ASM-006`'s DeepSeek-compatible client) rather than introducing a second text-AI vendor — no new vendor decision needed here, unlike Phase 11's image-gen vendor (`ASM-011`).
- **Dependencies:** Milestone 1 Phase 5 (a `Report` must exist to ground answers in) and Phase 6 (payment — chat is a paid-tier feature like the rest of the post-payment app).
- **API requirements:** New endpoint family, e.g. `POST /chat/messages`, `GET /chat/history` — not yet specified in `docs/api-specification.md`.
- **Database requirements:** New `Conversation`/`Message` entities — listed as Milestone 2 scope in `docs/database-design.md` §3, column-level schema written when this phase starts.
- **UI/UX requirements:** Chat bubble layout, suggested-prompt chips sourced from the user's own report content (not hardcoded per user — should vary by what the report actually flagged), streaming response rendering.
- **Security considerations:** The system prompt must explicitly instruct the model to decline medical/medication/diagnosis questions and redirect to a professional — this is a **behavioral requirement to test for**, not just a nice-to-have (see `FR-019`'s hard rule); treat a chat response that gives direct medical/drug advice as a release-blocking defect, same severity class as the auth reuse-detection and payment-bypass tests in Milestone 1. Questionnaire answers feeding the chat context carry the same sensitivity `docs/security.md` §7 already flags for the narrative-generation call.
- **Testing requirements:** A dedicated test asserting a medication-adjacent question (e.g. "can I use minoxidil / retinoid / accutane") produces a refusal-and-redirect response, not medical advice — mirrors this project's existing "release-blocking behavioral test" pattern (auth reuse-detection, payment-bypass).
- **Acceptance criteria:** A user can ask a free-text question and get a report-grounded answer; the 3–4 suggested prompts work as one-click starters; a medication/medical question is declined with a professional-referral redirect, verified by an automated test, not just manual spot-checking.
- **Prerequisites:** None beyond Milestone 1 completeness — this phase has no open blocking item comparable to Phase 11's vendor decision.
- **Expected deliverables:** Working chat feature; `D:\zzz\chat-assistant\plans.md` executed.
- **Potential risks:** Prompt-injection via a crafted user question trying to extract system-prompt content or bypass the medical-advice refusal — treat as a real security test case, not just a UX concern. Ongoing per-message AI cost (`BR-006`) scales with usage in a way the single narrative call doesn't — flag to the client same as Phase 11's cost note.
- **Open questions:** None blocking.

## Phase 13 — Settings & Billing Restructure

**Objective:** Split the current single-page Dashboard `ProfileCard` into a dedicated Settings area (Account Info / Password / Billing), per `FR-021`.

- **Scope:** New `/settings` route with its own left-nav (Account Info, Password, Billing), migrating the existing profile/password-change UI (`ASM-009`'s v1.13 implementation) out of the Dashboard page into this new area; Billing sub-page shows current product/price, Stripe payment action, a visually-present-but-disabled PayPal action (`OI-3`), and payment history (reusing the existing `GET /payments` data, `docs/api-specification.md` §8).
- **Modules/features included:** `settings-billing`.
- **Functional requirements:** `FR-021`.
- **Technical requirements:** None new — this is a UI restructuring of existing data (`GET /users/me`, `GET /payments`, the existing `change-password` endpoint), not new backend surface, unless `OI-3` is resolved toward "yes, wire up real PayPal," in which case that becomes its own scoped addition.
- **Dependencies:** Milestone 1 Phase 1 (auth/password-change), Phase 6 (payment history), Phase 7 (existing profile UI being migrated).
- **API requirements:** None new (composition of existing endpoints), unless PayPal is greenlit (`OI-3`).
- **Database requirements:** None new.
- **UI/UX requirements:** A persistent Settings entry point from the user menu (matching the reference's pattern), distinct from the main Report/AI Visuals/Chat Assistant nav; must preserve the existing `BR-009`/`BR-010` toast/confirm-dialog conventions already implemented in the current `ProfileCard`.
- **Security considerations:** None beyond what's already enforced for `/users/me` and `/payments` (per-user scoping, already correct).
- **Testing requirements:** Regression tests confirming the migrated password-change/profile flows still work identically after relocating them out of the Dashboard.
- **Acceptance criteria:** Settings area is reachable, shows account info, supports password change (no session revocation, matching current behavior), and shows accurate billing/payment history; the Dashboard's old inline `ProfileCard` is removed, not duplicated.
- **Prerequisites:** None blocking.
- **Expected deliverables:** Working Settings/Billing area; `D:\zzz\settings-billing\plans.md` executed.
- **Potential risks:** Low — this is largely a relocation of already-working functionality, not new logic (same risk profile Milestone 1's Phase 7 noted for itself).
- **Open questions:** None — `OI-3` resolved as `BR-012` (PayPal ships visible but disabled), see `milestone2_requirements.md` §5.

---

## Related Documents

- [`milestone2_requirements.md`](./milestone2_requirements.md) — the requirements this plan sequences.
- [`phase-wise-requirements.md`](./phase-wise-requirements.md) — the Milestone 1 equivalent of this document; Phases 10–13 above continue its numbering.
- [`client_requirements.md`](./client_requirements.md) — governing source of truth.
