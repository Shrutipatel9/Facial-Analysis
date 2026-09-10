# Security

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`AUTH-010`–`AUTH-012`, `ASM-001`, `BR-005`/`CON-006`). Auth-flow mechanics live in [`docs/authentication.md`](./authentication.md) — this file covers cross-cutting posture and production hardening.

**Status:** Draft, derived from `client_requirements.md` **v1.4** (+ production hardening).

---

## 1. Scope of This Document

- Credential and secret handling
- Token storage + CSRF for cookie sessions
- HTTP security headers / CSP
- Photo validation as a safety gate
- Third-party data exposure
- Production deploy checklist
- What is explicitly **not** covered yet (Phase 2 / deferred)

## 2. Credential & Secret Handling

| Item | Requirement |
|---|---|
| Passwords | **Argon2id** via `pwdlib` (`PasswordHash.recommended()`) — decided during authentication implementation. Never plaintext. |
| OTP values | Hashed at rest, never plaintext (`AUTH-011`). |
| Refresh tokens | Stored server-side by token hash, not the raw token (`AUTH-010`). |
| API keys (OpenAI, Stripe, email provider) | Backend-only environment configuration; never in the frontend bundle — **[Assumption]**. |
| JWT / OTP pepper | Fail-fast at startup if placeholders (`change-me…`) are used. |

## 3. Token Storage (v1.4)

- **Access token:** in-memory Zustand only (15 min). Never `localStorage` / `sessionStorage` / Zustand `persist`.
- **Refresh token:** httpOnly cookie, `Path=/`, `SameSite=Strict`, `Secure` when `ENVIRONMENT != development`. First-party on the frontend origin via the Next.js `/api/backend` rewrite.
- **`reset_token` (v1.5, `AUTH-015`):** short-lived (~10 min), single-use, JSON-body-carried only — never a cookie, never Zustand. Signed with the same secret as access tokens but carries a distinct `purpose: "password_reset"` claim; `get_current_user` rejects any token whose purpose isn't `"access"`, so it can never be replayed as a Bearer credential. Single-use is enforced by binding it to a fingerprint of the account's password hash at mint time — the reset itself changes that hash, so a captured/replayed token fails closed (`RESET_TOKEN_INVALID`) rather than needing a server-side revocation table.
- Residual XSS risk is limited to the short-lived access token — mitigate with CSP + encoding + dependency hygiene (`ASM-001`).

## 4. CSRF (cookie-authenticated endpoints)

Cookie endpoints (`POST /auth/refresh`, `POST /auth/logout`) require:

1. Header `X-Requested-With: XMLHttpRequest` (blocks simple HTML form CSRF).
2. When `Origin` or `Referer` is present, it must match `CORS_ORIGINS`.

Bearer-only APIs are not CSRF-sensitive (cross-site forms cannot set `Authorization`). Rate limit on refresh: **30/minute**. `/auth/forgot-password`, `/auth/reset-password/verify`, and `/auth/reset-password` are neither cookie- nor Bearer-authenticated (their credential is request-body content — an OTP or `reset_token`), so CSRF defenses don't apply to them either, for the same reason they don't apply to `/auth/register` or `/auth/login`.

## 5. HTTP Security Headers

| Header | Frontend (Next.js) | Backend (FastAPI) |
|---|---|---|
| `Content-Security-Policy` | Yes (connect-src `'self'` for proxy) | — |
| `Strict-Transport-Security` | Production only | Production only |
| `X-Frame-Options: DENY` | Yes | Yes |
| `X-Content-Type-Options: nosniff` | Yes | Yes |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Same |
| `Permissions-Policy` | `camera=(self)` (photo-capture, `FR-005`, needs it — see `CameraCapture.tsx`); mic/geo/payment disabled | `camera=()`; mic/geo/payment disabled (the API never serves the camera-using page) |
| `poweredByHeader` | Disabled | — |
| OpenAPI `/docs` | — | Disabled outside development |

CSP currently allows `'unsafe-inline'` / `'unsafe-eval'` for Next.js compatibility; nonce-based CSP is a follow-up hardening step.

## 6. Photo Validation as a Security/Quality Gate (BR-005, CON-006)

Because Phase 1 auto-publishes reports with no admin review (`BR-002`), enforced photo validation is not just a UX nicety — it is the only safety gate between an unusable/adversarial input and a paying user's report (`BR-004`). **`ASM-002`'s threshold deferral is now resolved** — implemented in `Backend/app/services/photo_validation_service.py`, run via MediaPipe's lightweight `FaceDetector` (BlazeFace short-range) + Pillow/OpenCV for pixel-level checks. All seven per-photo checks below always run and are always all reported (not just failures), for the rejection-reason UI (`docs/ui-ux-design.md` §3.4, `docs/api-specification.md` §5):

| Check | Method | Threshold |
|---|---|---|
| `file_readable` | `PIL.Image.open` decode | Must decode; short-circuits the rest if it doesn't (all remaining checks reported as skipped-failed, not silently omitted) |
| `resolution` | Shortest side, px | ≥ 640px |
| `brightness` | Grayscale mean luminance (0–255) | 60–200 |
| `face_count` | MediaPipe detections | Exactly 1 (0 → "no face detected", ≥2 → "multiple faces detected") |
| `frame_proportion` | Face bounding-box area ÷ image area | 0.15–0.80 |
| `occlusion` | Overall detection confidence | ≥ 0.75 |
| `pose_match` | Nose-tip x-offset from eye-midpoint, normalized by eye span (`estimate_yaw_ratio`) | `\|ratio\|` < 0.12 reads as frontal; classified pose must match the angle slot being uploaded to |

**These are delivery-team decisions (`ASM-002`), not client-stated** — reasonable defaults, expect a tuning pass once real device photos go through Phase 4/5 integration.

**Set-level identity check (`ASM-010`, v1.15) — not a per-photo check.** The seven checks above only ever look at one photo in isolation; nothing caught a different person's photo being uploaded for one required angle (user-reported). Once all three required angles individually pass, `check_photo_set_identity` compares a 5-ratio landmark signature (eye/nose/mouth/jaw/face width, normalized by inter-ocular distance, via the same `FaceLandmarker` model `facial_measurement_service.py` uses) across all three photos and flags whichever one has the largest total distance to the other two. `IDENTITY_MISMATCH_THRESHOLD = 0.6`, empirically calibrated (not assumed) — see `ASM-010` in `client_requirements.md` for the measured same-person vs. different-person distance ranges. Enforced in the UI (`PhotoSetCompleteStep.tsx` blocks Continue) and independently server-side at both `POST /payments/checkout` and `POST /analysis` (`PhotoIdentityMismatchError`, 409) so it can't be bypassed by calling either endpoint directly.

**Occlusion is a simplified heuristic, not a real glasses/hat classifier.** `NormalizedKeypoint.score` and `.label` are always `0.0`/`None` for the BlazeFace short-range model — verified empirically against a real portrait during implementation, not documented anywhere in MediaPipe's own docs — so per-feature (eyes/mouth) confidence isn't available. The check falls back to the detector's overall confidence score at a stricter floor than `face_count`'s own detection threshold (0.75 vs. 0.5). A known limitation, not a gap to silently paper over.

A request-level 15MB size cap (`PHOTO_MAX_UPLOAD_BYTES`) and content-type allow-list (JPEG/PNG/HEIC — DNG rejected, see `docs/api-specification.md` §5) are enforced before any of the above (decompression-bomb/DoS concern) — a real 4xx, not a `validation_result` entry.

**Do not relax this gate to "checklist only"** — that reintroduces the risk `BR-004`/`CON-006` exist to prevent.

## 7. Third-Party Data Exposure

| Third party | Data sent | Note |
|---|---|---|
| AI provider (DeepSeek, `ASM-006`) | Facial measurements + questionnaire answers + **the three photos themselves (base64)** (`FR-008`) | **Updated (facial-analysis-engine):** the photos are sent too, not just derived measurements — multimodal, matching `FR-008`'s "not photo analysis alone" / `NFR-008`'s literal "Vision" naming. Sensitive self-perception content and biometric-adjacent photo data — treat as sensitive in transit/at rest. Vendor is DeepSeek, not the client-stated OpenAI — see `docs/database-design.md` §2.6, `docs/client_requirements.md` `ASM-006`. |
| Stripe | Payment details | **Implemented (Phase 6, v1.11):** no raw card data ever reaches our backend or frontend — checkout redirects to Stripe's own hosted Checkout page (`checkout.Session.create(mode="payment")`), and our client sends only a `user_id` in session metadata (no `report_id` — none exists yet at payment time, see `docs/database-design.md` §2.8), never card fields. |
| Email/OTP provider | User email, OTP code | Vendor TBD (`NFR-012`). |

**Webhook signature verification (Phase 6):** `POST /payments/webhook` is deliberately unauthenticated (no `get_current_user`) — Stripe itself is the caller, not a logged-in user. Trust instead comes from verifying the `Stripe-Signature` header against the **raw** request body via `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`; a missing/invalid signature is rejected (400 `INVALID_WEBHOOK_SIGNATURE`) before any `Payment` row is touched. The webhook is the only trusted source of payment truth — a client-side redirect back to `success_url` is never treated as proof of payment, only as a UX cue to refetch (`ReportScreen.tsx`).

## 8. Production Deploy Checklist

- [ ] `ENVIRONMENT=production` (enables `Secure` cookies, HSTS, TrustedHost, disables `/docs`)
- [ ] Strong unique `JWT_SECRET` and `OTP_PEPPER` (not placeholders)
- [ ] `CORS_ORIGINS` = exact frontend origin(s), HTTPS, no `*`
- [ ] `TRUSTED_HOSTS` set only if the API is publicly reachable by hostname (leave empty behind an internal rewrite)
- [ ] Frontend `NEXT_PUBLIC_API_URL=/api/backend` (same-origin proxy) — do **not** point the browser at the API origin
- [ ] `BACKEND_URL` = internal FastAPI URL (server-only)
- [ ] TLS terminated in front of Next.js (and API if exposed)
- [ ] Postgres not publicly reachable; backups configured
- [ ] `EMAIL_PROVIDER=smtp` (or equivalent) with real credentials
- [ ] Confirm `refresh_token` cookie: HttpOnly, Secure, SameSite=Strict, Path=/
- [ ] Confirm security headers present on HTML responses
- [ ] Confirm refresh without `X-Requested-With` returns 403
- [ ] Rate limits exercised under load for login/register/OTP/refresh

**Deploy topology (required for this cookie model):** browser → Next.js (HTTPS) → rewrite `/api/backend/*` → FastAPI. Do not switch to a cross-site API hostname without revisiting `SameSite` and CSRF.

## 9. Explicitly Not Covered Yet

- Formal data-retention/privacy policy — Phase 2.
- Admin RBAC beyond the reserved `role` field — Phase 2.
- Nonce-based CSP (no `'unsafe-inline'` / `'unsafe-eval'`) — follow-up.

## 10. Open Items

| Item | Status |
|---|---|
| Photo validation exact thresholds | Deferred (`ASM-002`) |
| Password hashing algorithm | **Resolved — Argon2id** |
| Data retention policy | Phase 2 |
| Nonce CSP | Follow-up hardening |

## 11. Related Documents

- [`docs/authentication.md`](./authentication.md)
- [`docs/architecture.md`](./architecture.md)
- [`docs/testing-strategy.md`](./testing-strategy.md)
