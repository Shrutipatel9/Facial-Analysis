# Authentication

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`AUTH-*`, `FE-*`, `WF-002`, `ASM-001`). This is the deep-dive referenced by [`docs/architecture.md`](./architecture.md) §3 — read that section first for the layering contract this document elaborates on.

**Status:** Draft, derived from `client_requirements.md` v1.1. **This flow is fully specified by the client — do not redesign it.** In particular: **do not use Supabase Auth or any third-party identity provider** (`AUTH-001`, `CON-002`); Supabase is Postgres hosting only.

---

## 1. Non-Negotiable Constraints

| ID | Constraint |
|---|---|
| AUTH-001 | Custom, backend-controlled auth. No Supabase Auth or any auth-as-a-service. |
| AUTH-002 | JWT access token + refresh token pair. |
| AUTH-005 | Backend APIs solely responsible for authentication and authorization — no delegation. |
| FE-002 | Both tokens stored in the Redux auth store — explicitly **not** `localStorage`. |

## 2. Flow Shape (identical for signup and login)

Both signup and login are the same two-step shape (`AUTH-003`): **(1)** email + password, **(2)** mandatory OTP verification. OTP is a required second step in both flows, never an alternative to the password step.

```
Step 1: Email + Password
  Signup: validate email not already registered → hash password → create pending/unverified user record
  Login:  validate credentials against stored hash
  (Neither path issues tokens yet — both proceed to Step 2)
          │
          ▼
Step 2: OTP Verification
  Backend generates OTP → stores hashed, with expiry → emails it (NFR-012)
  User submits OTP → backend checks hash + expiry + attempt/lockout limits (AUTH-011)
          │
          ├─ success → signup: mark account verified · login: confirm session
          │            → issue JWT access token + refresh token pair (AUTH-002, AUTH-012)
          │            → flow completes
          │
          └─ failure → increment attempt counter
                       → after 5 failed attempts, 15-minute lockout before another OTP can be requested
```

## 3. Authenticated Request Lifecycle

1. **Request:** frontend API client attaches the access token to each request (`FE-004`).
2. **Validation:** backend validates the JWT on protected routes before allowing access (`AUTH-007`).
3. **Refresh:** when the access token expires (15 min), the frontend calls the refresh endpoint with the refresh token → backend validates it against the revocation store (`AUTH-010`) → issues a new access token and **rotates** the refresh token → frontend updates the Redux auth store transparently (`FE-005`), invisible to the UI.
4. **Reuse detection:** if a refresh token that was already rotated out is presented again, the **entire token family is revoked** and the user must re-authenticate — this is a theft signal, not a normal error path.
5. **Logout:** frontend calls logout → backend revokes the refresh token server-side (`AUTH-010`) → frontend clears the Redux auth store (`FE-006`).
6. **Session expiry / invalid session:** any refresh failure (expired, revoked, or reused/rotated-out token) → backend returns an auth error → frontend clears Redux auth state and redirects to login (`FE-006`).

## 4. Security Parameters (settled — do not rederive)

These were explicitly delegated to the delivery team by the client ("decide by yourself considering security") and are now fixed values, not open questions:

| Parameter | Value | ID |
|---|---|---|
| OTP expiry | 10 minutes | `AUTH-011` |
| OTP resend cooldown | 60 seconds | `AUTH-011` |
| OTP failed-attempt lockout | 5 attempts → 15-minute lockout | `AUTH-011` |
| OTP storage | Hashed, never plaintext | `AUTH-011` |
| Access token lifetime | 15 minutes | `AUTH-012` |
| Refresh token lifetime | 30 days, rotated on every use | `AUTH-012` |
| Refresh token reuse detection | Whole token family revoked on reuse | `AUTH-012` |

## 5. Server-Side Session Model

`AUTH-010`: refresh tokens must be revocable server-side. This requires a store of issued/rotated refresh tokens **keyed by a token identifier, not the raw token** — see `Refresh Token / Session Record` in [`docs/database-design.md`](./database-design.md) (`DATA-003`), which also carries rotation lineage to support the reuse-detection rule above.

## 6. Frontend Token Management

| ID | Requirement |
|---|---|
| FE-001 | Auth state managed via Redux / Redux Toolkit. |
| FE-002 | Access + refresh tokens live in the Redux auth store, not `localStorage` (client-confirmed, overriding the earlier default recommendation). |
| FE-003 | Centralized in a single auth slice/service — not duplicated across components. |
| FE-004 | Access token automatically attached to authenticated requests via a centralized API client/interceptor. |
| FE-005 | Expired access token triggers a silent refresh-and-retry, transparent to the UI, where possible. |
| FE-006 | Invalid session (refresh fails/revoked) clears auth state and redirects to login. |
| FE-007 | Auth logic stays out of UI components — UI never talks to auth APIs or handles tokens directly. |

## 7. Roles

`AUTH-008`/`AUTH-009`: the User data model carries a `role` field. Phase 1 populates only `"user"`; this exists so an `"admin"` role can be introduced in Phase 2 (see `docs/brd.md` §4) without a schema rework. Role/permission enforcement beyond this reserved field is not otherwise specified for Phase 1, since there is only one functional role.

## 8. Residual Risk (ASM-001 — document, don't "fix")

Storing both tokens in Redux (not `localStorage`) avoids a script scraping tokens out of generic browser storage across sessions/tabs, which is the specific risk many XSS payloads target by default. It does **not** eliminate XSS exposure in principle: any script executing in the page's own JS context can, in theory, still reach in-memory Redux state. This is a **settled implementation decision**, not an open question — the client explicitly chose it. The actual mitigation layer is standard XSS hardening (CSP, output encoding, dependency hygiene), covered in [`docs/security.md`](./security.md). Do not propose moving tokens to `httpOnly` cookies as a "fix" — that was considered and explicitly rejected in favor of Redux (`OQ-009`, resolved).

## 9. Endpoints (summary — full contracts in api-specification.md)

| Endpoint | Purpose |
|---|---|
| `POST /auth/register` | Step 1 of signup (email + password) |
| `POST /auth/login` | Step 1 of login (email + password) |
| `POST /auth/otp/verify` | Step 2 of both flows (OTP submission) |
| `POST /auth/otp/resend` | Re-send OTP, subject to the 60s cooldown |
| `POST /auth/refresh` | Exchange refresh token for a new access token (rotates refresh token) |
| `POST /auth/logout` | Revoke the current refresh token server-side |

Full request/response shapes: [`docs/api-specification.md`](./api-specification.md) §Authentication.

## 10. Open Items

None outstanding for authentication itself — `OQ-001`, `OQ-003`, `OQ-005` (ORM, tangential), and `OQ-009` are all resolved in `client_requirements.md` v1.1. The only related open item is the **specific OTP email vendor** (`NFR-012` — channel is confirmed as email, provider TBD, non-blocking); see `docs/architecture.md` §7.

## 11. Related Documents

- [`docs/architecture.md`](./architecture.md) §3 — the mandated layering this flow implements.
- [`docs/security.md`](./security.md) — broader security posture, including this flow's trade-offs.
- [`docs/database-design.md`](./database-design.md) — `User`, `OTP Record`, `Refresh Token / Session Record` entities.
- [`docs/api-specification.md`](./api-specification.md) — endpoint contracts.
