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
| `POST /auth/register` | Step 1 of signup: email + password + **full_name** (v1.13, `FR-017`) → creates pending/unverified user, triggers OTP | No | `AUTH-003`, `WF-002` |
| `POST /auth/login` | Step 1 of login: email + password → validates credentials, triggers OTP | No | `AUTH-003`, `WF-002` |
| `POST /auth/otp/verify` | Step 2 of both flows: submit OTP → on success issues access token (JSON) + refresh token (**httpOnly cookie**) | No (OTP is the credential at this step) | `AUTH-003`, `AUTH-011`, `WF-002` |
| `POST /auth/otp/resend` | Re-issue OTP, subject to 60s cooldown | No | `AUTH-011` |
| `POST /auth/refresh` | Cookie credential → new access token; rotates refresh cookie; revokes family on reuse | No (refresh cookie is the credential) | `AUTH-010`, `AUTH-012` |
| `POST /auth/logout` | Revoke current refresh session server-side; clear refresh cookie | Yes | `AUTH-010`, `FE-006` |
| `GET /auth/me` | Current authenticated user (used by AuthHydrator after refresh on startup) | Yes | `FE-002` v1.4, `AUTH-014` |
| `POST /auth/forgot-password` | Step 1 of reset: `{email}` → always-generic response; issues OTP (purpose=`password_reset`) only if the account exists | No | `AUTH-015` |
| `POST /auth/reset-password/verify` | Step 2 of reset: `{email, otp}` → on success, `{reset_token, expires_in}` | No (OTP is the credential at this step) | `AUTH-011`, `AUTH-015` |
| `POST /auth/reset-password` | Step 3 of reset: `{reset_token, new_password}` → updates password, revokes every session for the account | No (`reset_token` is the credential at this step — see below) | `AUTH-010`, `AUTH-015` |
| `POST /auth/change-password` | **Added v1.13.** In-app password change: `{current_password, new_password}` → verifies the current password (not an OTP/reset_token), updates it. Deliberately does **not** revoke the caller's session (contrast `reset-password`) — see ASM-009's revision in `client_requirements.md` | Yes | `FR-017` |

**Token transport (v1.4):** `otp/verify` and `refresh` return `{ access_token, token_type, expires_in, user }` in JSON (`otp/verify` always included `user`; `refresh` also returns `user` so startup restore is one round-trip). The refresh token is **never** in the JSON body — the backend sets/rotates/clears it via `Set-Cookie` on `refresh_token`. The Next.js frontend calls the API through a **same-origin rewrite** (`/api/backend/*` → FastAPI) so the httpOnly cookie is first-party on the frontend origin and survives reload / tab close / browser restart.

**`reset_token` (v1.5, `AUTH-015`):** a short-lived (~10-minute), single-use, purpose-scoped JWT — JSON-body-carried only, never a cookie. It shares the access token's signing secret but carries `purpose: "password_reset"` instead of `"access"`, so it is **never** valid as an `Authorization: Bearer` credential on any protected endpoint, regardless of its remaining TTL. It is bound to a fingerprint of the account's password hash at mint time, so it self-invalidates (and any replay is rejected as `RESET_TOKEN_INVALID`) the instant a reset actually completes.

## 3. User Profile — **Implemented (Phase 7)**

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `GET /users/me` | Current user profile for the dashboard's Profile card. Aliases `GET /auth/me` with `created_at` added ("member since"); includes `full_name` (v1.13) | Yes | `FR-017` |

**`PATCH /users/me` still not built (revised v1.13).** The original delivery-team decision here (Phase 7's first pass) was that profile management should be fully view-only, since `DATA-001` had no editable field. The user then directly instructed two revisions: (1) capture a `full_name` at signup and use it for the dashboard greeting instead of an email-derived guess (`POST /auth/register` now requires it, `DATA-001` gained the column — `docs/database-design.md` §2.1), and (2) let a user change their password in-app without an editable-name-style `PATCH` (`POST /auth/change-password`, §2, not this router). `full_name` itself is still only set once at signup, not edited afterward via any endpoint — so `PATCH /users/me` remains unbuilt, just for a narrower reason than before. See `ASM-009`'s revision in `client_requirements.md`.

## 4. Onboarding Questionnaire

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `GET /questionnaire` | Retrieve the fixed 25-entry question set (23 questions + 2 conditional follow-ups) + disclaimer text | Yes | `FR-003` |
| `GET /questionnaire/status` | `{completed: bool}` — has this user already submitted a response | Yes | `FR-003` (supports the auto-route-into-questionnaire-until-done UX) |
| `POST /questionnaire/responses` | Submit answers; rejected server-side if `disclaimer_accepted` is not true or a required visible answer is missing/invalid | Yes | `FR-003`, `FR-004`, `BR-003` |

Content is finalized — see [`docs/onboarding_questionnaire_spec.md`](./onboarding_questionnaire_spec.md) (client-sourced) and `Backend/app/services/questionnaire_service.py`. `GET /questionnaire` returns each question's `id`, `number`, `text`, `type` (`text`/`single_select`/`multi_select`/`yes_no`), `options`, `required`, and an optional `show_if` (`{question_id, in_values}`) — the entire branching model is this one relationship, reused for `q19` and for the `q9`/`q11` follow-ups. `POST /questionnaire/responses` takes `{answers: {[question_id]: string | string[]}, disclaimer_accepted: boolean}`; error codes `DISCLAIMER_NOT_ACCEPTED` (422) and `QUESTIONNAIRE_ANSWERS_INVALID` (422, carries per-question `details`). An answer submitted for a question that isn't currently visible under its `show_if` condition is silently dropped, not rejected — see `docs/database-design.md` §2.4.

## 5. Photo Upload & Validation

Implemented in `photo-upload-validation` (`Backend/app/api/routers/photos.py`). Angle set (3-angle default, `ASM-005` not yet client-confirmed) and per-photo capture guidance are specified in [`docs/photo_capture_spec.md`](./photo_capture_spec.md).

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /photos` | `multipart/form-data`: `angle`, `capture_method` (`upload`\|`camera`), `file`. Validates synchronously and returns the outcome — see below. Upserts by `(user_id, angle)`: a retry replaces the existing row for that angle, not a new one. | Yes | `FR-005`, `FR-006`, `BR-005` |
| `GET /photos/status` | Per-angle status (`angle`, `label`, `instruction`, `photo`\|`null`) + `completed: bool` (`BR-004`) — mirrors `GET /questionnaire/status`'s shape, echoes each angle's label/instruction so the frontend never needs its own copy of the angle set. Plus `identity_check: {consistent, mismatched_angles, message}\|null` (v1.15, shape revised v1.18) — `null` until `completed` is true, since there's nothing to compare before then; `mismatched_angles` is a list of angle ids that don't match the others (empty when consistent) — usually one, but names both non-front angles when all three photos are mutually inconsistent, since there's no meaningful way to single one of those out (`ASM-010`) | Yes | `BR-004`/`BR-005` (supports the same auto-route-until-done UX as the questionnaire) |
| `GET /photos/{id}` | Retrieve validation status/result for a specific photo; 404 generic if not found or not owned | Yes | `BR-005` |
| `GET /photos/{id}/file` | The actual stored image bytes (raw response, `Content-Type` set from the stored file's extension), not JSON — lets the frontend show a real, persistent preview of an already-uploaded angle after a reload instead of only the ephemeral upload-time blob: URL | Yes | Supports `docs/ui-ux-design.md` §3.4's preview requirement |

**`POST /photos` always returns `200`, not 201** (a request can be a first upload or a replace) — a photo that decodes fine but fails a quality check is not an HTTP error, it's a normal response with `validation_status: "failed"`. Only a malformed *request* (unknown angle, missing/oversized/wrong-type file, undecodable image) is a real 4xx (`PHOTO_ANGLE_UNKNOWN`, `PHOTO_UPLOAD_INVALID`, both 422). Uploading once every required angle already has a passed photo returns 409 `PHOTO_SET_ALREADY_COMPLETE` (one-and-done, same posture as the questionnaire's no-resubmission rule).

Response body (`PhotoOut`): `{id, angle, capture_method, validation_status: "passed"|"failed", checks: [{check, passed, reason}, ...], uploaded_at}` — `checks` always lists all six checks (not just failures), per `docs/ui-ux-design.md` §3.4's rejection-reason UI. Six checks, thresholds in `docs/security.md` §6: `file_readable`, `resolution`, `brightness`, `face_count`, `frame_proportion`, `occlusion`.

A failed validation returns which check(s) failed, and `is_photo_set_ready()` (the single `BR-004` enforcement point, `Backend/app/services/photo_service.py`) must **not** allow the analysis pipeline to be triggered from a rejected set — the eventual `POST /analysis` endpoint (§6) must call this same function as its first guard clause.

Supported upload file types: JPEG, PNG, HEIC. **DNG/RAW is not supported** — real RAW decoding needs `rawpy`/`libraw`, a much heavier dependency than the web-upload flow's realistic needs justify right now; flagged as an explicit follow-up, not silently dropped (see `D:\zzz\photo-upload-validation\plans.md`).

## 6. Facial Analysis

Implemented in `facial-analysis-engine` (`Backend/app/api/routers/analysis.py`). **Resolved:** processing is an in-process asyncio background task + polling, not a synchronous blocking request and not a new task-queue (Celery/Redis) — no queue exists anywhere in this stack, and a single background call didn't justify adding one.

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /analysis` | Trigger; guards on questionnaire submitted (409 `QUESTIONNAIRE_NOT_SUBMITTED`) then photo set ready (409 `PHOTO_SET_NOT_READY`) then (v1.15) cross-photo identity consistency (409 `PHOTO_IDENTITY_MISMATCH`, redundant with `/payments/checkout`'s own check — defense in depth) then **a succeeded payment (402 `PAYMENT_REQUIRED`)** then no existing non-failed analysis (409 `ANALYSIS_ALREADY_EXISTS`); returns 200 `{id, status: "processing"}` immediately, runs CV/MediaPipe measurements **and** the DeepSeek narrative call together as one background task. Still a user-facing "Start Analysis" click (`components/analysis/AnalysisScreen.tsx`), same as before payment gating existed — only reachable once payment has already succeeded. The Stripe webhook (§8) does **not** call this itself; it only flips `Payment.status` | Yes | `FR-007`, `FR-008`, `BR-004`, `BR-001`, `ASM-010` |
| `GET /analysis/status` | `{status: "none"\|"processing"\|"completed"\|"failed", analysis_id: string\|null}` — mirrors `GET /photos/status`'s shape; lets the frontend guard/page recover state after a reload without caching an id client-side | Yes | Supports the same auto-route-until-done UX as photos/questionnaire |
| `GET /analysis/{id}` | Full result: `measurements` (always once completed), `narrative_result` (nullable — see below), `error_message` (if failed); 404 generic if not found/not owned | Yes | `FR-007`, `FR-008` |

A `"failed"` analysis may be retried via `POST /analysis` again (a new row) — `"processing"`/`"completed"` may not, same one-and-done posture as the questionnaire/photos.

**Pay-before-analysis (v1.11 revision):** `status`/`measurements`/`narrative_result` are now all produced together in one pipeline run, only ever started after payment has already succeeded — there is no more free/paid split. `status` reaches `"completed"` once CV measurements succeed; if the DeepSeek narrative call itself then fails, `narrative_result` stays `null` but `status` remains `"completed"` (the user already paid and has valid measurements) — a manual pipeline re-invoke is the practical retry, not an automated one yet. See `docs/database-design.md` §2.6.

**AI vendor (`ASM-006`):** built against **DeepSeek**, not the client-stated OpenAI (`NFR-008`) — see `docs/database-design.md` §2.6, `docs/security.md` §7. **Multimodal:** the request to the AI includes the three photos (base64) alongside the CV measurements and questionnaire answers, matching `FR-008`'s "not photo analysis alone."

## 7. Reports

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /reports` | Idempotent get-or-create: assembles a report from the user's completed (and, by construction, already-paid) analysis result (`BR-002`); 409 `ANALYSIS_NOT_COMPLETED` if analysis isn't done. Returns the same report on a repeat call rather than erroring, unlike `POST /analysis` — cheap/safe to retry since assembly is AI-free | Yes | `FR-009`–`FR-014` |
| `GET /reports/{id}` | Retrieve report — `teaser` (intro + one-line-per-feature) and `full` (everything else); `full` is always populated, no payment-status field | Yes | `FR-015` |
| `GET /reports/{id}/pdf` | Lazily renders and caches the PDF on first call, then streams the cached bytes | Yes | `FR-013` |
| `GET /reports` | List a user's reports (today: 0 or 1, see `database-design.md` §5) for the dashboard | Yes | `FR-017` |

**Resolved (v1.9):** report generation is synchronous, not async/polling like `POST /analysis` — assembly is a pure, AI-free data transform of the analysis result's current `measurements`/`narrative_result` (`docs/database-design.md` §2.7), so no `GET /reports/status` endpoint exists or is needed.

**No payment-awareness here (v1.11 revision):** payment gates the *start* of analysis itself (§6, `BR-001`), not report reads — a `Report` can only ever be created from an already-`"completed"` analysis, which by construction never exists without a preceding succeeded payment. `get_or_create_report`/`get_report` still re-run `assemble_sections()` on every read (cheap, no I/O) — kept not for a pre/post-payment transition (that no longer exists) but for the one remaining case a narrative can still be null post-payment: the DeepSeek call itself failing after CV succeeded. When a manual pipeline retry later succeeds, the next report read picks up the real content automatically, and `pdf_reference` is cleared so a stale cached PDF isn't served. The bypass-attempt test that used to live here (`TestBR001BypassAttempt`) now lives against `POST /analysis` instead (§6) — see `Backend/tests/integration/test_payment_flow.py`.

## 8. Payment — **Implemented (Phase 6, v1.11)**

| Method & Path | Purpose | Auth required | Requirement ID |
|---|---|---|---|
| `POST /payments/checkout` | No request body (nothing to reference — no report/analysis exists yet). Guards on questionnaire submitted (409), photo set ready (409), and (v1.15) cross-photo identity consistency (409 `PHOTO_IDENTITY_MISMATCH`) — same prerequisites `POST /analysis` itself checks; creates a Stripe Checkout Session (`mode="payment"`) using the **configurable** price/currency, inserts a `pending` `Payment` row, returns `{checkout_url}`. 409 `ALREADY_PAID` if a `succeeded` payment already exists for this user | Yes | `FR-015`, `FR-016`, `OQ-002`, `ASM-010` |
| `GET /payments/status` | `{status: "unpaid"\|"pending"\|"succeeded", price_cents, price_currency}` — mirrors `GET /questionnaire/status`/`GET /photos/status`'s shape; used by both the frontend payment guard and the `/payment` paywall page (so price is never hardcoded client-side) | Yes | `FR-016`, `OQ-002` |
| `POST /payments/webhook` | Stripe webhook receiver. Verifies `Stripe-Signature` against the raw request body (`stripe.Webhook.construct_event`) — 400 `INVALID_WEBHOOK_SIGNATURE` on failure. On `checkout.session.completed`: flips the matching `Payment.status` to `"succeeded"` **only** — does **not** call `analysis_service.trigger_analysis` itself (a deliberate choice: the pipeline can finish in a couple of seconds, and auto-triggering it made the "analyzing" step invisible to the user). The user starts analysis themselves via `POST /analysis` (§6) once back in the app, now unblocked. On `checkout.session.expired`/`payment_intent.payment_failed`: `status="failed"`. An unrecognized `stripe_session_id` is acknowledged (200), not errored — Stripe expects a 200 for events it can't act on | No (Stripe-signed via header + raw body, not user-authenticated — deliberately has no `get_current_user` dependency) | `FR-015` |
| `GET /payments` | Payment history for the calling user only, for the dashboard | Yes | `FR-017` |

`OQ-002` (price) is explicitly open — `checkout` reads `REPORT_PRICE_CENTS`/`REPORT_PRICE_CURRENCY` from configuration, copying the value onto the `Payment` row at creation time so a later price change never affects an in-progress payment (see `docs/database-design.md` §2.8). Real Stripe API calls are never made in automated tests — the Stripe client is monkeypatched (`payment_service.get_stripe_client()`, same posture as `ai_narrative_service.get_ai_client()`), per `BR-006`. No raw card data ever reaches this backend — the client redirects to Stripe's own hosted Checkout page; see `docs/security.md` §7. Verified live end-to-end with real Stripe test-mode Checkout (Stripe CLI webhook forwarding), not just mocked automated tests.

## 9. Dashboard — **Implemented (Phase 7)**

Dashboard is a composition of `GET /users/me`, `GET /reports`, and `GET /payments` (§3, §7, §8) rather than a dedicated endpoint — no separate dashboard-specific data is implied by `FR-017` beyond what those three already expose. `frontend/src/app/(protected)/dashboard/page.tsx` renders each as its own independently-loading section (report status/download, payment history, profile) so one slow/failed section never blocks the others.

## 10. Explicitly Not Built (Phase 2)

No endpoints for: admin report review/approval, email notification triggers, PayPal, AI Visual Features, AI Beauty Assistant chat. See `docs/brd.md` §3.2.

## 11. Open Items

| Item | Status |
|---|---|
| Report price value/model | Open (`OQ-002`) — endpoint contract must stay price-agnostic. |
| Analysis endpoint sync/async mechanism | **Resolved** — in-process background task + polling, see §6 above. |
| Photo storage/retrieval mechanism | **Resolved** — `DatabasePhotoStorage` default, `GET /photos/{id}/file` retrieval, see `docs/database-design.md` §2.5. |
| Multiple reports per user | **Resolved** — one per user, `/reports` returns 0 or 1 today, no pagination needed — see `docs/database-design.md` §5. |
| Report generation sync/async mechanism | **Resolved** — synchronous, AI-free data transform, no polling endpoint — see §7 above. |
| Payment gating mechanism | **Resolved (Phase 6, v1.11)** — Stripe hosted Checkout + webhook; the gate sits on `POST /analysis` itself (`PaymentRequiredError`, 402), not on report reads — see §6/§8 above. |
| When analysis (CV + the paid AI narrative call) happens | **Resolved (Phase 6, v1.11)** — both run together, in one pipeline pass, only ever reachable via a user-facing "Start Analysis" click once payment has already succeeded; the webhook itself only flips `Payment.status`, it does not trigger the pipeline — see §6/§8 above and `docs/database-design.md` §2.6. |

## 12. Related Documents

- [`docs/authentication.md`](./authentication.md) — full auth flow and security parameters behind §2.
- [`docs/database-design.md`](./database-design.md) — entities each endpoint reads/writes.
- [`docs/architecture.md`](./architecture.md) — layering these endpoints are called through.
