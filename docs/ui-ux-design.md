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

### 3.1 Landing Page
Single, clear CTA leading into signup (`FR-001`). No further content requirements are client-specified — **[Recommendation]**: standard marketing structure (hero, value proposition, CTA), left to the delivery team per `CON-003`.

### 3.2 Auth Screens (Signup / Login / OTP)
- Signup and login share the same two-step interaction shape (email+password → OTP) — see `docs/authentication.md` §2. The UI should reuse one OTP-entry component for both flows rather than building two.
- OTP screen must surface: countdown/expiry (10 min), a resend action respecting the 60s cooldown, and a clear lockout message after 5 failed attempts (15 min) — these are the exact values in `AUTH-011`, not placeholders.
- Per `FE-007`, none of these screens talk to auth APIs directly — they dispatch to the Zustand auth store, which the API client acts on (see `docs/architecture.md` §3).

### 3.3 Onboarding Questionnaire
- 23 questions with branching logic (`FR-003`); the literal question text/branching tree is not in `client_requirements.md` and is flagged as an open item in `docs/prd.md` §7 — do not invent questionnaire content beyond the stated categories (medical conditions/medications, self-perceived best feature, comfort with recommendation types, appearance-thought frequency, similar lifestyle/self-perception questions).
- Must end in the disclaimer checkbox (`FR-004`); submission is disabled until checked (`BR-003`) — this must be enforced in the UI **and** re-validated server-side (client-side-only gating is insufficient given `BR-003` is a hard rule).

### 3.4 Photo Requirements & Upload
- Guideline checklist is shown **before** upload (`FR-005`): remove glasses/hat, natural even lighting, plain white background, tie back long hair, remove makeup, avoid neck-covering clothing, no filters.
- The checklist is informational, not the enforcement mechanism — actual validation happens server-side (`FR-006`). The UI must handle a rejection response with a specific reason and let the user retry, rather than treating upload as fire-and-forget.

### 3.5 Processing State
No specific UX requirement stated beyond the pipeline existing (`FR-007`/`FR-008`). **[Recommendation]**: an async/polling or websocket-driven progress state, since MediaPipe/OpenCV processing + an OpenAI call are not instant — exact mechanism is a technical decision for `docs/api-specification.md` / the `facial-analysis-engine` module plan, not a UI-only concern.

### 3.6 Results / Report / Payment
- A teaser may be shown pre-payment; the full report is locked until Stripe payment succeeds (`FR-015`, `BR-001`). The UI must distinguish these two states clearly rather than showing a blurred/truncated full report (which is an implementation choice, not specified — **[Recommendation]**: an explicit teaser summary distinct from the gated content).
- Full report view must present all 11 features (`FR-009`) each with narrative + before/after framing + summary callout (`FR-010`), plus the report-level intro/preamble/limitations/recommendations sections (`FR-011`).
- PDF export/download action must be available from both the report view and the dashboard (`FR-013`, `FR-017`).

### 3.7 Dashboard
Report history/status, download, payment history, profile management (`FR-017`). No further structural requirement is client-stated.

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
| Literal 23-question set and branching tree | Not in `client_requirements.md` — needed before `onboarding-questionnaire` implementation (see `docs/prd.md` §7). |
| Visual branding/design system | No assets exist yet (`CON-003`) — delivery team decides for Phase 1. |
| Accessibility/responsive/localization requirements | Not client-stated — **[Assumption]** that standard responsive/basic-accessibility practice applies; not confirmed. |
| Processing-state UX mechanism (polling vs. websocket) | Technical decision, not yet made — see `facial-analysis-engine` module plan. |

## 6. Related Documents

- [`docs/prd.md`](./prd.md) §4 — the workflow these screens implement.
- [`docs/authentication.md`](./authentication.md) — exact auth-screen behavior/parameters.
- [`docs/api-specification.md`](./api-specification.md) — endpoints each screen calls (via the API client).
