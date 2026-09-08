# API Specification

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`AUTH-001`–`AUTH-015`, `WF-002`, `FR-*`). This is a **preliminary, high-level contract** — request/response field-level schemas will be finalized during each module's implementation (see each module's `plans.md` under `D:\zzz\`), not fixed here.

**Status:** Draft. Backend framework: FastAPI, Python (`NFR-001` — v1.2 had briefly changed this to Next.js Route Handlers under a since-reverted single-app consolidation; v1.3 reverts to FastAPI, see `client_requirements.md` change log). The Frontend (Next.js) is a separate application calling these endpoints cross-origin. All endpoints below are versionless placeholders (e.g. `/auth/...`) pending an actual routing convention decision at implementation time — these map to FastAPI router files (e.g. `app/api/routers/auth.py`), but the logical path/method contract below is unaffected by that file-layout detail.

---

## 1. Conventions

- All protected endpoints require a valid JWT access token (`AUTH-007`); unauthenticated requests to them return 401.
- Error responses should carry a machine-readable reason where the client UI must branch on it (e.g. photo-validation failure reason, OTP lockout) — exact error schema is an implementation decision, not client-specified.
- Endpoints that touch configurable business values (report price) must read from configuration, never a hardcoded literal (`OQ-002`).

## 2. Authentication (see docs/authentication.md for full flow)

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /auth/register` | Step 1 of signup: email + password → creates pending/unverified user, triggers OTP | No | `AUTH-003`, `WF-002` |
| `POST /auth/login` | Step 1 of login: email + password → validates credentials, triggers OTP | No | `AUTH-003`, `WF-002` |
| `POST /auth/otp/verify` | Step 2 of both flows: submit OTP → on success issues access token (JSON) + refresh token (**httpOnly cookie**) | No (OTP is the credential at this step) | `AUTH-003`, `AUTH-011`, `WF-002` |
| `POST /auth/otp/resend` | Re-issue OTP, subject to 60s cooldown | No | `AUTH-011` |
| `POST /auth/refresh` | Cookie credential → new access token; rotates refresh cookie; revokes family on reuse | No (refresh cookie is the credential) | `AUTH-010`, `AUTH-012` |
| `POST /auth/logout` | Revoke current refresh session server-side; clear refresh cookie | Yes | `AUTH-010`, `FE-006` |
| `GET /auth/me` | Current authenticated user (used by AuthHydrator after refresh on startup) | Yes | `FE-002` v1.4, `AUTH-014` |
| `POST /auth/forgot-password` | Step 1 of reset: `{email}` → always-generic response; issues OTP (purpose=`password_reset`) only if the account exists | No | `AUTH-015` |
| `POST /auth/reset-password/verify` | Step 2 of reset: `{email, otp}` → on success, `{reset_token, expires_in}` | No (OTP is the credential at this step) | `AUTH-011`, `AUTH-015` |
| `POST /auth/reset-password` | Step 3 of reset: `{reset_token, new_password}` → updates password, revokes every session for the account | No (`reset_token` is the credential at this step — see below) | `AUTH-010`, `AUTH-015` |

**Token transport (v1.4):** `otp/verify` and `refresh` return `{ access_token, token_type, expires_in, user }` in JSON (`otp/verify` always included `user`; `refresh` also returns `user` so startup restore is one round-trip). The refresh token is **never** in the JSON body — the backend sets/rotates/clears it via `Set-Cookie` on `refresh_token`. The Next.js frontend calls the API through a **same-origin rewrite** (`/api/backend/*` → FastAPI) so the httpOnly cookie is first-party on the frontend origin and survives reload / tab close / browser restart.

**`reset_token` (v1.5, `AUTH-015`):** a short-lived (~10-minute), single-use, purpose-scoped JWT — JSON-body-carried only, never a cookie. It shares the access token's signing secret but carries `purpose: "password_reset"` instead of `"access"`, so it is **never** valid as an `Authorization: Bearer` credential on any protected endpoint, regardless of its remaining TTL. It is bound to a fingerprint of the account's password hash at mint time, so it self-invalidates (and any replay is rejected as `RESET_TOKEN_INVALID`) the instant a reset actually completes.

## 3. User Profile

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `GET /users/me` | Current user profile for dashboard (may alias or complement `GET /auth/me`) | Yes | `FR-017` |
| `PATCH /users/me` | Basic profile management | Yes | `FR-017` |

## 4. Onboarding Questionnaire

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `GET /questionnaire` | Retrieve the (branching) question set | Yes | `FR-003` |
| `POST /questionnaire/responses` | Submit answers; rejected server-side if `disclaimer_accepted` is not true | Yes | `FR-003`, `FR-004`, `BR-003` |

The exact shape of the branching question set is not finalized (see `docs/prd.md` §7) — `GET /questionnaire` may need to return conditional next-question logic once that content exists.

## 5. Photo Upload & Validation

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /photos` | Upload one angle of a multi-angle photo set; runs backend validation synchronously or returns a pending-validation state | Yes | `FR-005`, `FR-006`, `BR-005` |
| `GET /photos/{id}` | Retrieve validation status/result for a specific photo | Yes | `BR-005` |

A failed validation must return which check(s) failed (per `docs/ui-ux-design.md` §3.4), and must **not** allow the analysis pipeline to be triggered from a rejected set (`BR-004`).

## 6. Facial Analysis

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /analysis` | Trigger MediaPipe/OpenCV measurement + OpenAI narrative generation for a validated photo set + questionnaire response | Yes | `FR-007`, `FR-008` |
| `GET /analysis/{id}` | Poll analysis status/result (processing is not instant — see `docs/ui-ux-design.md` §3.5) | Yes | `FR-007`, `FR-008` |

Whether analysis is synchronous, polled, or pushed (websocket) is an implementation decision for the `facial-analysis-engine` module plan — not fixed here.

## 7. Reports

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /reports` | Assemble and auto-publish a report from an analysis result (`BR-002`) | Yes | `FR-009`–`FR-014` |
| `GET /reports/{id}` | Retrieve report — teaser fields pre-payment, full content post-payment (`BR-001`) | Yes | `FR-015` |
| `GET /reports/{id}/pdf` | Download PDF export — should itself enforce the payment gate, not rely on the UI alone | Yes | `FR-013`, `BR-001` |
| `GET /reports` | List a user's reports for the dashboard | Yes | `FR-017` |

**The payment gate must be enforced server-side on every report-content and PDF endpoint**, not only hidden in the UI — this follows directly from `BR-001` being a business rule, not a display preference.

## 8. Payment

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /payments/checkout` | Create a Stripe checkout/payment session for a given report, using a **configurable** price | Yes | `FR-015`, `FR-016`, `OQ-002` |
| `POST /payments/webhook` | Stripe webhook receiver confirming payment success/failure | No (Stripe-signed, not user-authenticated) | `FR-015` |
| `GET /payments` | Payment history for the dashboard | Yes | `FR-017` |

`OQ-002` (price) is explicitly open — `checkout` must read price from configuration so the eventual pricing decision doesn't require an API contract change.

## 9. Dashboard

Dashboard is a composition of `GET /users/me`, `GET /reports`, and `GET /payments` (§3, §7, §8) rather than a dedicated endpoint — no separate dashboard-specific data is implied by `FR-017` beyond what those three already expose.

## 10. Explicitly Not Built (Phase 2)

No endpoints for: admin report review/approval, email notification triggers, PayPal, AI Visual Features, AI Beauty Assistant chat. See `docs/brd.md` §3.2.

## 11. Open Items

| Item | Status |
|---|---|
| Report price value/model | Open (`OQ-002`) — endpoint contract must stay price-agnostic. |
| Analysis endpoint sync/async mechanism | Not decided — see `docs/ui-ux-design.md` §3.5. |
| Photo storage/retrieval mechanism | Not decided — see `docs/database-design.md` §5. |
| Multiple reports per user | Not decided — affects whether `/reports` needs pagination/filtering beyond a simple list — see `docs/database-design.md` §1. |

## 12. Related Documents

- [`docs/authentication.md`](./authentication.md) — full auth flow and security parameters behind §2.
- [`docs/database-design.md`](./database-design.md) — entities each endpoint reads/writes.
- [`docs/architecture.md`](./architecture.md) — layering these endpoints are called through.
