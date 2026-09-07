# Phase-Wise Requirements

**Source of truth:** [`client_requirements.md`](./client_requirements.md). This document sequences the client's **Phase 1 delivery scope** (see `docs/brd.md` §3.1) into internal **Implementation Phases 0–9**.

> **Naming disambiguation — read this first.** `client_requirements.md` uses "Phase 1" / "Phase 2" to mean *client delivery scope* (Phase 1 = build now, Phase 2 = deferred future engagement). Every implementation phase in this document (Phase 0 through Phase 9) sits entirely **inside** the client's Phase 1. Do not confuse the two numbering schemes. Where this document says "Phase 3," it always means "Implementation Phase 3," never the client's delivery Phase.

**Status:** Draft, derived from `client_requirements.md` v1.1.

---

## Phase Overview & Module Map

| Implementation Phase | Name | Module(s) | `plans.md` location |
|---|---|---|---|
| 0 | Project Foundation | `project-foundation` | `D:\zzz\project-foundation\plans.md` |
| 1 | Authentication & Authorization | `authentication` | `D:\zzz\authentication\plans.md` |
| 2 | Landing Page & Onboarding Questionnaire | `landing-page`, `onboarding-questionnaire` | `D:\zzz\landing-page\plans.md`, `D:\zzz\onboarding-questionnaire\plans.md` |
| 3 | Photo Upload & Validation | `photo-upload-validation` | `D:\zzz\photo-upload-validation\plans.md` |
| 4 | Facial Analysis Engine | `facial-analysis-engine` | `D:\zzz\facial-analysis-engine\plans.md` |
| 5 | Report Generation & Auto-Publish | `report-generation` | `D:\zzz\report-generation\plans.md` |
| 6 | Payment Integration | `payment` | `D:\zzz\payment\plans.md` |
| 7 | User Dashboard | `user-dashboard` | `D:\zzz\user-dashboard\plans.md` |
| 8 | Testing & Hardening | cross-cutting — no dedicated module | — (see `docs/testing-strategy.md`) |
| 9 | Deployment & Production Readiness | cross-cutting — no dedicated module | — |

Phases 8 and 9 are process phases, not feature modules — they don't get a `D:\zzz\<module>\plans.md` of their own (see Final Validation summary at the end of this doc for why).

Dependency chain: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9**, strictly linear, because each phase's data depends on the previous one (auth before anything user-owned; questionnaire+photos before analysis; analysis before report; report before payment gates it; report+payment before dashboard has anything to show).

---

## Phase 0 — Project Foundation

**Objective:** Establish the base repo structure, tooling, and cross-cutting infrastructure (config, DB connection, base API client, base Redux store) that every later phase builds on, without implementing any business feature yet.

- **Scope:** Backend project skeleton (FastAPI app structure, SQLAlchemy engine/session setup, Alembic initialized), frontend project skeleton (Vite/React app structure, Redux Toolkit store shell, base API client with interceptor scaffolding), environment/config management, base error-handling conventions.
- **Modules/features included:** `project-foundation` only.
- **Functional requirements:** None directly — this phase enables `FR-*` implementation, it doesn't implement any.
- **Technical requirements:** `NFR-001`–`NFR-006` (stack choices), `NFR-011` (clean/modular structure) applied to the skeleton itself.
- **Dependencies:** None — this is the root phase.
- **API requirements:** No business endpoints; a `/health` endpoint (already present in `Backend/app/main.py`) is sufficient at this stage.
- **Database requirements:** Alembic initialized and connected to Supabase Postgres (`NFR-002`/`NFR-003`); no business tables yet.
- **UI/UX requirements:** None (no user-facing screens yet).
- **Security considerations:** Secret/config management pattern established (env vars, never committed) — see `docs/security.md` §2 for what must never leak to the frontend bundle.
- **Testing requirements:** Test framework selection and a smoke test proving the pipeline runs (see `docs/testing-strategy.md` §6).
- **Acceptance criteria:** Backend boots and connects to the database; frontend boots and renders a placeholder shell; an empty Alembic migration applies cleanly; the base API client and Redux store exist (empty) per the layering in `docs/architecture.md` §3.
- **Prerequisites:** None.
- **Expected deliverables:** Runnable backend/frontend skeletons; Alembic wired up; `D:\zzz\project-foundation\plans.md` executed.
- **Potential risks:** Under-designing the module-boundary convention here (`docs/architecture.md` §5) causes rework in every later phase — get this right before Phase 1 starts.
- **Open questions:** Test framework choice (`docs/testing-strategy.md` §6); no others specific to this phase.

## Phase 1 — Authentication & Authorization

**Objective:** Deliver the complete custom email+password+OTP authentication flow, end to end, per `docs/authentication.md`.

- **Scope:** Backend auth endpoints, JWT/OTP services, Redux auth slice, API client token attachment/refresh, all six auth-lifecycle flows in `docs/authentication.md` §2–3.
- **Modules/features included:** `authentication`.
- **Functional requirements:** `FR-002`.
- **Technical requirements:** `AUTH-001`–`AUTH-012`, `FE-001`–`FE-007`.
- **Dependencies:** Phase 0 (DB connection, base API client/Redux store, config management for JWT secret and OTP provider credentials).
- **API requirements:** `docs/api-specification.md` §2 (register, login, otp/verify, otp/resend, refresh, logout).
- **Database requirements:** `User`, `OTP Record`, `Refresh Token / Session Record` (`docs/database-design.md` §2.1–2.3).
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.2 (signup/login/OTP screens, session-expiry redirect).
- **Security considerations:** Full content of `docs/authentication.md` §4–8 (fixed OTP/token parameters, reuse detection, Redux storage trade-off) and `docs/security.md` §2–3.
- **Testing requirements:** `docs/testing-strategy.md` §2 auth row in full, including the reuse-detection case flagged as a release blocker.
- **Acceptance criteria:** A user can sign up and log in via the two-step flow; an expired access token silently refreshes; a reused rotated-out refresh token revokes the whole session family and forces re-login; logout revokes server-side; no token ever appears in `localStorage`.
- **Prerequisites:** Phase 0 complete. Decision made on password hashing algorithm and OTP email vendor (`docs/security.md` §7, `docs/architecture.md` §7).
- **Expected deliverables:** Working auth flow across frontend+backend; `D:\zzz\authentication\plans.md` executed; `docs/authentication.md` cross-checked against the actual implementation.
- **Potential risks:** Getting refresh-token rotation/reuse-detection wrong is a security-critical bug, not a cosmetic one — this is the single highest-risk item in this phase (see `docs/testing-strategy.md` §3).
- **Open questions:** OTP email vendor choice (`NFR-012`, non-blocking); password hashing algorithm (not client-specified).

## Phase 2 — Landing Page & Onboarding Questionnaire

**Objective:** Give a logged-in user the entry marketing page and the full onboarding questionnaire, ending in the mandatory disclaimer gate.

- **Scope:** Landing page (public), 23-question branching questionnaire, disclaimer checkbox gate.
- **Modules/features included:** `landing-page`, `onboarding-questionnaire`.
- **Functional requirements:** `FR-001`, `FR-003`, `FR-004`.
- **Technical requirements:** None beyond the standard stack; questionnaire state is regular app state, not auth state (does not go in the Redux auth slice).
- **Dependencies:** Phase 1 (a user must be authenticated before submitting a questionnaire response tied to their account).
- **API requirements:** `docs/api-specification.md` §4.
- **Database requirements:** `Questionnaire Response` (`docs/database-design.md` §2.4).
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.1, §3.3.
- **Security considerations:** Server-side re-validation of `disclaimer_accepted` (`BR-003`) — client-side gating alone is insufficient.
- **Testing requirements:** `docs/testing-strategy.md` §2 rows for `FR-001`, `FR-003`/`FR-004`/`BR-003`.
- **Acceptance criteria:** Landing page CTA routes into signup; questionnaire submission is impossible without the disclaimer checked, enforced by the backend even if the UI is bypassed.
- **Prerequisites:** **Blocking prerequisite specific to this phase:** the literal 23-question set and branching tree must be sourced/confirmed before implementation steps in `D:\zzz\onboarding-questionnaire\plans.md` can be finalized (see `docs/prd.md` §7). This is the single most consequential open item in the whole documentation set — flag it to the client early, since it blocks this phase's real implementation start even though planning can proceed.
- **Expected deliverables:** Landing page; full questionnaire flow with disclaimer gate; `D:\zzz\landing-page\plans.md` and `D:\zzz\onboarding-questionnaire\plans.md` executed.
- **Potential risks:** Starting questionnaire implementation before the question set is confirmed risks building the wrong branching logic and reworking it later.
- **Open questions:** Literal question/branching content (blocking, see above).

## Phase 3 — Photo Upload & Validation

**Objective:** Let a user upload a multi-angle photo set with an enforced backend validation gate.

- **Scope:** Photo requirements/checklist screen, multi-angle upload, backend validation pipeline, rejection-with-reason handling.
- **Modules/features included:** `photo-upload-validation`.
- **Functional requirements:** `FR-005`, `FR-006`.
- **Technical requirements:** Validation checks per `BR-005` (face count, frame proportion, occlusion, resolution, brightness) — exact thresholds set during this phase (`ASM-002`), not before.
- **Dependencies:** Phase 1 (uploads are tied to an authenticated user); does not depend on Phase 2's questionnaire content, only on the user existing.
- **API requirements:** `docs/api-specification.md` §5.
- **Database requirements:** `Photo` (`docs/database-design.md` §2.5); resolve the open storage-mechanism question (§5 of that doc) in this phase.
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.4.
- **Security considerations:** `docs/security.md` §4 — this gate is a safety mechanism given Phase 1's no-review auto-publish (`BR-004`, `CON-006`), not just UX polish; do not weaken it under schedule pressure.
- **Testing requirements:** `docs/testing-strategy.md` §2 rows for `FR-005`/`FR-006`/`BR-005` and `BR-004`.
- **Acceptance criteria:** Each of the five validation checks independently triggers a correctly-reasoned rejection; a fully compliant photo set passes; no downstream analysis can be triggered from a rejected set.
- **Prerequisites:** Phase 1 complete. Validation thresholds decided and documented in `docs/security.md` §7 before this phase is marked done (per `client_requirements.md`'s own instruction to document them once implemented).
- **Expected deliverables:** Working upload+validation flow; thresholds recorded in `docs/security.md`; `D:\zzz\photo-upload-validation\plans.md` executed.
- **Potential risks:** Under-tuned thresholds either reject good photos (user friction) or admit bad ones (feeds a low-quality auto-published report, `BR-004`) — tune deliberately, not by guesswork, and revisit after Phase 4/5 integration testing.
- **Open questions:** Exact thresholds (resolved *during* this phase, per `ASM-002` — not before); photo storage mechanism.

## Phase 4 — Facial Analysis Engine

**Objective:** Build the from-scratch MediaPipe/OpenCV measurement pipeline and the OpenAI narrative-generation call that together produce the raw analysis feeding report generation.

- **Scope:** Landmark detection, per-feature measurement extraction, OpenAI prompt construction using measurements + questionnaire answers together.
- **Modules/features included:** `facial-analysis-engine`.
- **Functional requirements:** `FR-007`, `FR-008`.
- **Technical requirements:** `NFR-007` (MediaPipe/OpenCV, built from scratch), `NFR-008` (OpenAI Vision/GPT).
- **Dependencies:** Phase 2 (questionnaire answers must exist as OpenAI context) and Phase 3 (validated photos must exist as input) — this phase cannot start meaningfully before both.
- **API requirements:** `docs/api-specification.md` §6.
- **Database requirements:** `Facial Analysis Result` (`docs/database-design.md` §2.6).
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.5 (processing-state UX; sync/async mechanism decided in this phase).
- **Security considerations:** Questionnaire answers sent to OpenAI include sensitive self-perception/medical-adjacent content — see `docs/security.md` §5; treat as sensitive data in transit even absent a formal retention policy.
- **Testing requirements:** `docs/testing-strategy.md` §2 row for `FR-007`/`FR-008` — explicitly assert both measurements *and* questionnaire answers are present in the OpenAI request, not just one.
- **Acceptance criteria:** Given a validated photo set and a submitted questionnaire, the pipeline produces measurements for all 11 features and a narrative generation call that demonstrably used both inputs.
- **Prerequisites:** Phases 1–3 complete.
- **Expected deliverables:** Working analysis pipeline; `D:\zzz\facial-analysis-engine\plans.md` executed.
- **Potential risks:** This is the most technically novel phase (built from scratch, `NFR-007`) — schedule/complexity risk is highest here; OpenAI cost accumulation during development is the client's responsibility (`BR-006`) but should still be mocked in automated tests (`docs/testing-strategy.md` §4) to avoid unnecessary spend.
- **Open questions:** Sync vs. async analysis-endpoint mechanism (decided in this phase).

## Phase 5 — Report Generation & Auto-Publish

**Objective:** Assemble the 11-feature structured report from the analysis result, auto-publish it, and produce a branded PDF export.

- **Scope:** Report assembly (11 sections + report-level intro/preamble/limitations/recommendations), auto-publish state, PDF generation/export.
- **Modules/features included:** `report-generation`.
- **Functional requirements:** `FR-009`–`FR-014`.
- **Technical requirements:** In-house PDF branding (`FR-013`) — no client branding assets exist yet (`CON-003`), delivery team designs it.
- **Dependencies:** Phase 4 (a completed `Facial Analysis Result` is required as input).
- **API requirements:** `docs/api-specification.md` §7.
- **Database requirements:** `Report` (`docs/database-design.md` §2.7), including the forward-compatible `publish_state` field for Phase 2's future review workflow.
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.6 (full report view structure; teaser vs. gated distinction is designed here even though the payment gate itself is enforced in Phase 6).
- **Security considerations:** None specific beyond ensuring `publish_state` doesn't accidentally imply payment has occurred — publishing and payment-gating are separate concerns (`BR-002` vs. `BR-001`) and must not be conflated in this phase's implementation.
- **Testing requirements:** `docs/testing-strategy.md` §2 rows for `FR-009`–`FR-012`, `FR-013`, `FR-014`/`BR-002`.
- **Acceptance criteria:** Every generated report contains exactly the 11 features in `FR-009`, each with all three sub-elements (`FR-010`); report-level sections from `FR-011` are present; the report auto-publishes with no manual step; PDF export succeeds and matches the report content.
- **Prerequisites:** Phase 4 complete.
- **Expected deliverables:** Report assembly + PDF pipeline; `D:\zzz\report-generation\plans.md` executed.
- **Potential risks:** Conflating "published" with "payable/visible" would violate `BR-001` once Phase 6 adds the payment gate — design the teaser/full-content split now so Phase 6 only needs to add a gate, not restructure the report model.
- **Open questions:** Whether a user can have multiple reports (`docs/database-design.md` §5) — affects `report_id` cardinality assumptions made in this phase.

## Phase 6 — Payment Integration

**Objective:** Gate full report access behind a successful one-time Stripe payment.

- **Scope:** Stripe checkout session creation, webhook handling, server-side enforcement of the payment gate on report-content and PDF endpoints.
- **Modules/features included:** `payment`.
- **Functional requirements:** `FR-015`, `FR-016`.
- **Technical requirements:** `NFR-009` (Stripe only in Phase 1, no PayPal).
- **Dependencies:** Phase 5 (a report must exist to be gated).
- **API requirements:** `docs/api-specification.md` §8 — price must be read from configuration (`OQ-002`), never hardcoded.
- **Database requirements:** `Payment` (`docs/database-design.md` §2.8).
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.6 (payment screen, teaser-to-full transition on success).
- **Security considerations:** `docs/security.md` §5 (no raw card data handled by the backend; use Stripe's hosted/tokenized flow); the gate must be enforced server-side on every content/PDF endpoint (`docs/api-specification.md` §7), verified by direct authenticated API calls in testing, not just UI interaction.
- **Testing requirements:** `docs/testing-strategy.md` §2 rows for `FR-015`/`BR-001` and `FR-016`/`OQ-002` — the bypass-attempt test is a release blocker equivalent in importance to the auth reuse-detection test in Phase 1.
- **Acceptance criteria:** An unpaid report returns teaser-only (or 403) on every content/PDF endpoint, even via direct API call; a successful Stripe payment unlocks the specific report it was for; price is a configuration value.
- **Prerequisites:** Phase 5 complete. Report price still open (`OQ-002`) — implementation must not block on a final number, only on the value being configurable.
- **Expected deliverables:** Working payment gate; `D:\zzz\payment\plans.md` executed.
- **Potential risks:** A payment-gate bypass is a direct revenue-loss bug — treat any failure in the bypass-attempt test as blocking, not advisory.
- **Open questions:** `OQ-002` (final price) — explicitly kept open by the client; does not block this phase's implementation, only the eventual configured value.

## Phase 7 — User Dashboard

**Objective:** Give users a single place to see report history/status, download reports, view payment history, and manage their profile.

- **Scope:** Dashboard aggregation view (composition, not a new domain — see `docs/api-specification.md` §9), profile management.
- **Modules/features included:** `user-dashboard`.
- **Functional requirements:** `FR-017`.
- **Technical requirements:** None beyond composing existing endpoints.
- **Dependencies:** Phases 1, 5, 6 (needs auth, reports, and payments to have something to show).
- **API requirements:** Reuses `GET /users/me`, `GET /reports`, `GET /payments` (`docs/api-specification.md` §3, §7, §8) — no new backend surface unless aggregation-specific needs emerge during implementation.
- **Database requirements:** None new — reads existing entities.
- **UI/UX requirements:** `docs/ui-ux-design.md` §3.7.
- **Security considerations:** Standard per-user data isolation (a user must only see their own reports/payments) — not separately client-stated but implicit in every prior phase's "Yes" auth requirement; should already hold if Phases 1–6 enforced per-user scoping correctly.
- **Testing requirements:** `docs/testing-strategy.md` §2 row for `FR-017`.
- **Acceptance criteria:** Dashboard accurately reflects report/payment state immediately after each workflow transition (upload, analysis, publish, payment).
- **Prerequisites:** Phases 1, 5, 6 complete.
- **Expected deliverables:** Working dashboard; `D:\zzz\user-dashboard\plans.md` executed.
- **Potential risks:** Low — this phase is largely composition of prior work; the main risk is staleness (dashboard not reflecting a state change promptly) rather than new logic.
- **Open questions:** None specific to this phase.

## Phase 8 — Testing & Hardening

**Objective:** Close testing gaps across all modules and verify the full `WF-001` journey end-to-end, with particular attention to the two release-blocking security tests already flagged (Phase 1 reuse-detection, Phase 6 payment-gate bypass).

- **Scope:** Cross-module integration/E2E test coverage, security-specific test pass, hardening based on findings.
- **Modules/features included:** Cross-cutting — no dedicated module or `plans.md`; work is tracked against each existing module's own test-coverage gaps.
- **Functional/technical requirements:** All `FR-*`/`AUTH-*`/`BR-*` per the mapping in `docs/testing-strategy.md` §2.
- **Dependencies:** Phases 0–7 complete (there is nothing to test end-to-end before then).
- **API/Database/UI-UX requirements:** None new — this phase verifies, not builds.
- **Security considerations:** Full `docs/security.md` pass; explicit verification of the two release-blocking tests named in Phases 1 and 6.
- **Testing requirements:** Full `docs/testing-strategy.md` document, all sections.
- **Acceptance criteria:** Every `FR-*`/`AUTH-*`/`BR-*` in `client_requirements.md` has at least one passing test; the full `WF-001` journey passes E2E; both flagged security tests pass.
- **Prerequisites:** Phases 0–7 complete.
- **Expected deliverables:** Test suite meeting the above; any hardening fixes found along the way.
- **Potential risks:** Treating this phase as a formality rather than budgeting real time for it — given Phase 1 has no admin review gate anywhere in the product (`BR-002`), this phase is the only remaining safety net before production traffic.
- **Open questions:** None beyond those already carried from earlier phases (thresholds, pricing) which should be resolved by this point.

## Phase 9 — Deployment & Production Readiness

**Objective:** Make the system deployable, without committing to a specific hosting platform, since that decision is explicitly deferred by the client.

- **Scope:** Environment configuration management, containerization/build readiness, logging/observability basics, secrets management for production — all host-agnostic per `NFR-010`/`CON-007`.
- **Modules/features included:** Cross-cutting — no dedicated module or `plans.md`.
- **Functional requirements:** None — this phase is operational, not feature-bearing.
- **Technical requirements:** Must not assume a specific hosting platform's primitives (`docs/architecture.md` §6).
- **Dependencies:** Phase 8 (don't productionize before the system is verified).
- **API/Database/UI-UX requirements:** None new.
- **Security considerations:** Production secrets management (API keys for OpenAI/Stripe/email provider, JWT signing key) must not reuse development values — not separately client-stated, standard practice given the third-party integrations in `docs/architecture.md` §1.
- **Testing requirements:** Deployment smoke test (system boots and serves traffic in a production-like configuration) — not host-specific.
- **Acceptance criteria:** The system can be built/packaged and configured for a production environment without code changes, pending only the actual hosting decision.
- **Prerequisites:** Phase 8 complete. **Blocking on the actual hosting decision** for anything beyond host-agnostic readiness — do not pick a platform speculatively.
- **Expected deliverables:** Production-ready configuration/build artifacts; a short note (in this document or a future `docs/deployment.md`, not yet created) on what remains once hosting is chosen.
- **Potential risks:** Coupling readiness work to assumptions about a specific platform (e.g. a particular provider's managed cron/queue) would need rework once hosting is actually chosen — keep this phase deliberately generic.
- **Open questions:** `NFR-010`/`CON-007` — hosting platform, explicitly undecided and not currently needed.

---

## Cross-Phase Dependency Summary

```
Phase 0 (Foundation)
   │
   ▼
Phase 1 (Auth) ──────────────┐
   │                          │
   ▼                          │
Phase 2 (Landing+Onboarding)  │
   │                          │
   ▼                          │
Phase 3 (Photo Upload)        │
   │                          │
   ▼                          │
Phase 4 (Analysis Engine) ◄───┘ (needs both questionnaire answers AND validated photos)
   │
   ▼
Phase 5 (Report Generation)
   │
   ▼
Phase 6 (Payment) ─── gates ──► Phase 5's report content
   │
   ▼
Phase 7 (Dashboard) ◄── reads Phases 1, 5, 6 data
   │
   ▼
Phase 8 (Testing & Hardening)
   │
   ▼
Phase 9 (Deployment Readiness)
```

## Related Documents

Every document under `docs/` feeds this one and is cross-referenced per phase above: [`brd.md`](./brd.md), [`prd.md`](./prd.md), [`architecture.md`](./architecture.md), [`authentication.md`](./authentication.md), [`security.md`](./security.md), [`ui-ux-design.md`](./ui-ux-design.md), [`api-specification.md`](./api-specification.md), [`database-design.md`](./database-design.md), [`testing-strategy.md`](./testing-strategy.md). Module-level implementation detail lives in `D:\zzz\<module>\plans.md`, one per module named in the Phase Overview table.
