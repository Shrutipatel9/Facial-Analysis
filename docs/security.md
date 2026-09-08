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
| `Permissions-Policy` | camera/mic/geo/payment disabled | Same |
| `poweredByHeader` | Disabled | — |
| OpenAPI `/docs` | — | Disabled outside development |

CSP currently allows `'unsafe-inline'` / `'unsafe-eval'` for Next.js compatibility; nonce-based CSP is a follow-up hardening step.

## 6. Photo Validation as a Security/Quality Gate (BR-005, CON-006)

Because Phase 1 auto-publishes reports with no admin review (`BR-002`), enforced photo validation is not just a UX nicety — it is the only safety gate between an unusable/adversarial input and a paying user's report (`BR-004`). Recommended checks (thresholds deferred to development, `ASM-002`):

- Exactly one face detected.
- Face occupies a reasonable proportion of the frame.
- No obvious occlusion over eyes/mouth (glasses/hat).
- Minimum resolution.
- Basic brightness/exposure check.

**Do not relax this gate to "checklist only"** — that reintroduces the risk `BR-004`/`CON-006` exist to prevent.

## 7. Third-Party Data Exposure

| Third party | Data sent | Note |
|---|---|---|
| OpenAI | Facial measurements + questionnaire answers (`FR-008`) | Sensitive self-perception content — treat as sensitive in transit/at rest. |
| Stripe | Payment details | No raw card data on our backend; use Stripe hosted/tokenized flows — **[Recommendation]**. |
| Email/OTP provider | User email, OTP code | Vendor TBD (`NFR-012`). |

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
