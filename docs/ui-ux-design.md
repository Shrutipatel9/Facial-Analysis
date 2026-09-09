# UI/UX Requirements

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`FR-003`–`FR-005`, `FE-*`, Qoves reference materials). This document lists screens and interaction rules implied by the functional/auth requirements — it is not a visual design spec (no branding assets exist yet, `CON-003`; the delivery team owns visual design decisions for Phase 1).

**Status:** Draft, derived from `client_requirements.md` v1.1, updated for the v1.5 forgot-password redesign and cross-cutting toast/confirm-dialog conventions (`BR-009`, `BR-010`).

---

## 1. Design Constraints

| ID | Constraint |
|---|---|
| CON-003 | No client-supplied branding/design assets exist yet — the delivery team makes UI/branding decisions for Phase 1. Anything specific below (copy, exact layout) beyond what's cited to an FR/AUTH id is **[Recommendation]**, not client-stated. |
| FR-013 | Report PDF must be branded with the team's own in-house design. |

## 2. Screen Inventory (derived from WF-001 / WF-002)

| # | Screen | Primary requirement(s) |
|---|---|---|
| 1 | Landing page | `FR-001` |
| 2 | Sign up (email + password) | `AUTH-003` step 1 |
| 3 | Log in (email + password) | `AUTH-003` step 1 |
| 4 | OTP verification (shared by signup & login) | `AUTH-003` step 2, `AUTH-011` |
| 5 | Onboarding questionnaire (23 questions, branching) | `FR-003` |
| 6 | Disclaimer (BDD/informational-only, checkbox-gated) | `FR-004`, `BR-003` |
| 7 | Photo requirements / guideline checklist | `FR-005` |
| 8 | Photo upload (multi-angle) | `FR-005`, `FR-006` |
| 9 | Upload rejection state (validation failed, with reason) | `FR-006`, `BR-005` |
| 10 | Processing / analysis in progress | `FR-007`, `FR-008` |
| 11 | Results page — teaser (pre-payment) | `FR-015` |
| 12 | Payment (Stripe) | `FR-015`, `FR-016` |
| 13 | Full report view (post-payment) | `FR-009`–`FR-013` |
| 14 | Dashboard (report history/status, download, payment history, profile) | `FR-017` |
| 15 | Session-expired / re-login prompt | `FE-006` |
| 16 | Forgot-password: request email, verify code, set new password (three separate screens) | `AUTH-015` |

## 3. Screen-Level Notes

### 3.1 Landing Page — **Revised (v1.13)**
Single, clear CTA leading into signup (`FR-001`). No further content requirements are client-specified — **[Recommendation]**: standard marketing structure (hero, value proposition, CTA), left to the delivery team per `CON-003`. Header now also carries a "Sign in" link for returning visitors, and a scroll-animated "How it works" section (questionnaire → photos → analysis → report) sits below the hero, per direct user request — `frontend/src/components/landing/LandingPage.tsx`.

### 3.2 Auth Screens (Signup / Login / OTP)
- Signup and login share the same two-step interaction shape (email+password → OTP) — see `docs/authentication.md` §2. The UI should reuse one OTP-entry component for both flows rather than building two.
- OTP screen must surface: countdown/expiry (10 min), a resend action respecting the 60s cooldown, and a clear lockout message after 5 failed attempts (15 min) — these are the exact values in `AUTH-011`, not placeholders.
- Per `FE-007`, none of these screens talk to auth APIs directly — they dispatch to the Zustand auth store, which the API client acts on (see `docs/architecture.md` §3).

### 3.3 Onboarding Questionnaire
- 23 questions with branching logic (`FR-003`) — the literal content is finalized in [`docs/onboarding_questionnaire_spec.md`](./onboarding_questionnaire_spec.md) (client-sourced). One question per step (`frontend/src/components/questionnaire/QuestionnaireWizard.tsx`), a fixed "Question N / 23" progress indicator (matching the reference material's own counter — the denominator never changes even when `q19` is skipped), auto-routes an authenticated user here until completed (`useQuestionnaireGuard`, `docs/phase-wise-requirements.md` Phase 2). Only `q19` is conditional (shown when `q4` ∈ {Masculine, No Preference}); `q9`/`q11`'s Yes-answer follow-ups render inline on the same step as their parent question, not as separate steps.
- Must end in the disclaimer checkbox (`FR-004`); submission is disabled until checked (`BR-003`) — this must be enforced in the UI **and** re-validated server-side (client-side-only gating is insufficient given `BR-003` is a hard rule). Per §4.1, only the final submit shows a toast — step-to-step Next/Back navigation does not.

### 3.4 Photo Requirements & Upload
- Guideline checklist is shown **once, before any capture UI** (`FR-005`): remove glasses/hat, natural even lighting, plain white background, tie back long hair, remove makeup, avoid neck-covering clothing, no filters (`PhotoRequirementsStep.tsx`). Full flow spec: [`docs/photo_capture_spec.md`](./photo_capture_spec.md).
- After the checklist, one step per required angle (3 under the current `ASM-005` default) — `PhotoWizard.tsx` mirrors `QuestionnaireWizard.tsx`'s stepped-array orchestration. Each step offers a choice of **upload from device** (file picker, JPEG/PNG/HEIC) or **use camera** (live in-browser capture via `getUserMedia`, a faint per-angle guide overlay, shutter, `CameraCapture.tsx`) — both converge on the same preview + retake/continue step and submit through the same `POST /photos` validation path (`docs/api-specification.md` §5). Progress is shown as "N of 3 photos", auto-routes an authenticated user here (after the questionnaire) until completed (`usePhotoUploadGuard`, mirrors `useQuestionnaireGuard`'s pattern exactly — see `docs/phase-wise-requirements.md` Phase 3).
- The 9-item per-photo capture guidance (`docs/photo_capture_spec.md` §3) is shown as UI-facing tips during capture — informational, not the enforcement mechanism. Actual validation happens server-side (`FR-006`, six checks, `docs/security.md` §6). The UI handles a rejection response by showing the specific failed check(s) inline with a retry, rather than treating upload as fire-and-forget — per §4.1, each upload outcome (pass or fail) gets its own toast, plus one additional toast when the full set transitions to complete (a deliberate exception to the questionnaire's step-navigation toast rule, since each photo upload is already a complete, persisted, independently-outcome-bearing server action, not just wizard navigation).
- **Preview persists across a reload.** An already-uploaded angle shows its actual submitted image, not just a pass/fail badge, even after the page is refreshed — `PhotoCaptureStep.tsx` fetches the real stored bytes via `GET /photos/{id}/file` (`docs/api-specification.md` §5) the first time that angle is viewed without a local blob: URL cached yet. Fixed after an initial gap where the preview only lived in an upload-time blob: URL that never survived a reload.

### 3.5 Processing State
Implemented in `facial-analysis-engine` (`components/analysis/AnalysisScreen.tsx`). Three states, no specific UX requirement stated beyond the pipeline existing (`FR-007`/`FR-008`):
1. **Ready** (no analysis yet) — a short explanation and an explicit "Start analysis" button. Deliberately does **not** auto-fire on arrival (auto-routed here by `useAnalysisGuard` the same way `/photos` is) — an AI call that costs money and takes real time shouldn't fire silently the instant a guard redirects someone there.
2. **Processing** — a loading state, polls `GET /analysis/status` every 3s until it resolves. The copy tells the user they can safely leave and come back (state is server-side, not lost on navigation).
3. **Failed** — shows the recorded `error_message`, offers a "Try again" action (`POST /analysis` again — allowed after a failure, unlike a duplicate trigger while already processing/completed).

No dedicated **results** view this phase — on completion the guard's own effect redirects to `/dashboard`; the 11-section report view (`FR-009`–`FR-015`) is `report-generation`'s scope (Phase 5), not this one.

### 3.6 Results / Report / Payment
- A teaser may be shown pre-payment; the full report is locked until Stripe payment succeeds (`FR-015`, `BR-001`). The UI must distinguish these two states clearly rather than showing a blurred/truncated full report (which is an implementation choice, not specified — **[Recommendation]**: an explicit teaser summary distinct from the gated content).
- Full report view must present all 11 features (`FR-009`) each with narrative + before/after framing + summary callout (`FR-010`), plus the report-level intro/preamble/limitations/recommendations sections (`FR-011`).
- PDF export/download action must be available from both the report view and the dashboard (`FR-013`, `FR-017`).

**Resolved (v1.9, `report-generation`):** `/report` is reached via a "View your report" link from `/dashboard`, not the forced onboarding-guard chain (`questionnaire`→`photos`→`analysis` still ends at `/dashboard`; report generation happens invisibly, on demand). Two states, not three:
1. **Loading** — a brief spinner while `POST /reports` (idempotent get-or-create, synchronous, no AI call) resolves on first visit, or the existing report is fetched on a later visit.
2. **Loaded** — a condensed summary, restyled per `docs/report_design_spec.md`'s Meridian visual language (warm-paper cards, one feature icon each, a single terracotta accent rule) scoped to this page's own content area, not a site-wide theme change: a short intro, one compact row per feature (icon, name, "Measured"/"AI-assessed" badge, summary callout, narrative — no bullet list), and a disclaimer footer. No recommendations section and no closing-recommendations paragraph render on this page — full detail (including tiered recommendations) lives in the PDF download, which remains the complete `FR-013` artifact. "Download PDF" triggers a browser save of the lazily-rendered, cached PDF.

**Not implemented (out of `report-generation`'s scope):** `docs/report_design_spec.md`/`docs/report_template.md`'s full Phase 2 system — numeric scoring, confidence indicators, the Harmony Chart, the seven-pose evidence gallery, Before/After AI visualization, and in-report payment-locked states. Those require capabilities (a scoring engine, 7-pose capture, AI image generation, a `Payment` model) that don't exist yet and are explicitly Phase 2 scope per `client_requirements.md` §2.2/§12 — this page borrows only the Meridian visual language and content-discipline principles (evidence-first, concise, non-clinical tone), applied to Phase 1's actual 11-feature content.

**Resolved (v1.11, `payment`):** the report view itself was never restricted — per the user's direct instruction, payment gates the *start of analysis*, not report reads, so by the time `/report` is reachable at all, it was always already paid, and this page's Phase 5 always-full behavior turned out to be exactly right (no teaser/full conditional needed here after all). Instead, a new `/payment` screen sits between photo upload and analysis in the onboarding chain — a Meridian-styled paywall card (price via `GET /payments/status`, never hardcoded; "Unlock & Start Analysis" behind the existing `ConfirmDialog` per `BR-010`) shown before any analysis or report content exists. See `docs/api-specification.md` §6/§8, `D:\zzz\payment\plans.md`.

### 3.7 Dashboard — **Implemented (Phase 7), revised v1.13**
Report history/status, download, payment history, profile management (`FR-017`). No further structural requirement is client-stated. Implemented as a single sectioned `/dashboard` page (`frontend/src/app/(protected)/dashboard/page.tsx`): a condensed welcome header (using the account's `full_name`, added v1.13), then a report-status/download card, a payment-history card, and a profile card, each loading independently. Profile management shows account info plus an inline current/new/confirm-password change form (`POST /auth/change-password`, no sign-out — v1.13) — see `docs/client_requirements.md`'s `ASM-009` revision. A persistent "Dashboard" nav button sits in the app header (`(protected)/layout.tsx`, next to the account menu) so it's reachable from any protected page, not just via the logo or an automatic redirect.

### 3.8 Session Expiry
When a refresh attempt fails, the frontend must clear auth state and redirect to login (`FE-006`) — this should be a single, consistent redirect handled at the API-client level (per the layering in `docs/architecture.md` §3), not duplicated per-screen.

### 3.9 Forgot-Password (`AUTH-015`, v1.5)
Three separate screens, not one combined OTP+new-password screen — see `docs/authentication.md` §2.5 for the full flow this UI implements:
1. **Request** — email only. Always advances forward regardless of whether the account exists (anti-enumeration); no success/failure signal beyond that.
2. **Verify** — 6-digit code entry, reusing the same expiry/resend-cooldown/lockout display rules as the signup/login OTP screen (§3.2). On success, silently advances to step 3 — no toast (§4's "intermediate step" exception).
3. **Set new password** — new-password + confirm-password fields (must match before submit is allowed), reusing the same password-strength meter as signup. On success: toast + redirect to login.

## 4. Cross-Cutting UX Rules

- Auth state/token handling never appears in UI component logic (`FE-007`) — screens only dispatch actions/read Zustand store state.
- Any screen that depends on auth (onboarding onward) must respect the silent-refresh behavior (`FE-005`): an expired access token should not visibly interrupt the user mid-task.
- No accessibility, responsive-breakpoint, or localization requirements are stated by the client — **[Open Question/Assumption]**: flag with the client if these matter for Phase 1, otherwise treat as delivery-team defaults during implementation.

### 4.1 Toasts (`BR-009`, v1.5) [Decided by delivery team]
- Position: **top-right** (`Toaster` in `app/layout.tsx`), consistently across the app.
- Every user-initiated action with a real success/failure outcome shows **exactly one** toast — never silent, never a bare redirect with no feedback.
- Exception: an **intermediate** step that only advances to another screen without completing the underlying action (e.g. login/signup submitting to the OTP step, forgot-password's verify step advancing to the set-new-password screen) does not toast — only the step that actually *completes* the action does (OTP verify success on signup/login; the final password-reset submit).
- Exception: forgot-password's **request** step never gets a success toast, by the same anti-enumeration design that makes its API response always generic (§3.9) — no distinct "it worked" signal may exist there.
- Toasts are additive to, not a replacement for, inline accessible status text (e.g. the OTP screen's `aria-live` countdown/lockout region) — both coexist; the toast covers the end-of-action event, the inline text covers ongoing state a screen-reader user needs to track.
- Error messages should be specific whenever a better one is available (the centralized `getErrorMessage` helper surfaces the backend's own message rather than a generic fallback wherever possible) rather than a generic "Something went wrong."

### 4.2 Destructive Actions (`BR-010`, v1.5) [Decided by delivery team]
Every destructive or irreversible action (delete, logout, revoke, etc.) anywhere in the app must go through the shared `ConfirmDialog` component (`components/ui/confirm-dialog.tsx`) — a title, a short description of the consequence, and explicit Cancel/Confirm actions — before it executes. Never fire such an action directly from a click handler. Logout (the auth module's only destructive-ish action so far) is the reference implementation; every later module's delete-type actions must reuse the same component rather than building a bespoke dialog.

The dialog's backdrop must stay a light, subtle dim — a small black tint (`bg-black/15` on `AlertDialogOverlay`, `components/ui/alert-dialog.tsx`), **no heavy `backdrop-blur`** on the rest of the screen. The point is to focus attention on the dialog without visually disorienting the page behind it.

### 4.3 Interactive Element Affordances [Decided by delivery team, v1.5]
Any enabled, clickable action element — buttons, icon-toggles (e.g. the password show/hide toggle), dialog actions — must show `cursor-pointer` on hover. This is not automatic: browsers render a plain `<button>` with the default arrow cursor, not a pointer, unless `cursor-pointer` is set explicitly. The shared `Button` component (`components/ui/button.tsx`) sets this at the base-variant level (`disabled:cursor-not-allowed` when disabled) so every button in the app gets it for free; a one-off raw `<button>` (like `PasswordInput`'s toggle) must set it directly. Links are unaffected — browsers already give `<a>` a pointer cursor.

## 5. Open Items

| Item | Status |
|---|---|
| Visual branding/design system | No assets exist yet (`CON-003`) — delivery team decides for Phase 1. |
| Accessibility/responsive/localization requirements | Not client-stated — **[Assumption]** that standard responsive/basic-accessibility practice applies; not confirmed. |
| Processing-state UX mechanism (polling vs. websocket) | Technical decision, not yet made — see `facial-analysis-engine` module plan. |

## 6. Related Documents

- [`docs/prd.md`](./prd.md) §4 — the workflow these screens implement.
- [`docs/authentication.md`](./authentication.md) — exact auth-screen behavior/parameters.
- [`docs/api-specification.md`](./api-specification.md) — endpoints each screen calls (via the API client).
