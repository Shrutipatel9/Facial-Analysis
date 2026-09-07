# Authentication

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`AUTH-*`, `FE-*`, `WF-002`, `ASM-001`). This is the deep-dive referenced by [`docs/architecture.md`](./architecture.md) §3 — read that section first for the layering contract this document elaborates on.

**Status:** Draft, derived from `client_requirements.md` **v1.4**. **This flow is fully specified by the client — do not redesign the signup/login/OTP shape.** In particular: **do not use Supabase Auth or any third-party identity provider** (`AUTH-001`, `CON-002`).

> **v1.4 token-transport revision.** Refresh tokens travel as an **httpOnly cookie** set by the backend; only the short-lived access token lives in the in-memory Zustand store. This supersedes the v1.1–v1.3 reading of `FE-002` / `OQ-009` that placed both tokens in the client-side store. Access tokens must still never be written to `localStorage` / `sessionStorage`, and Zustand must never use `persist` middleware for auth.

---

## 1. Non-Negotiable Constraints

| ID | Constraint |
|---|---|
| AUTH-001 | Custom, backend-controlled auth. No Supabase Auth or any auth-as-a-service. |
| AUTH-002 | JWT access token + refresh token pair. |
| AUTH-005 | Backend APIs solely responsible for authentication and authorization — no delegation. |
| FE-002 (v1.4) | Access token + user live in the Zustand auth store (memory only). Refresh token is an **httpOnly** cookie — not Zustand, not `localStorage`, not `sessionStorage`. |

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
          │            → issue JWT access token (JSON body) + refresh token (httpOnly cookie)
          │            → frontend stores access token + user in Zustand; cookie persists the session
          │
          └─ failure → increment attempt counter
                       → after 5 failed attempts, 15-minute lockout before another OTP can be requested
```

## 3. Authenticated Request Lifecycle

1. **Request:** frontend API client attaches the access token (`Authorization: Bearer`) to each request (`FE-004`). Refresh cookie is sent automatically via `credentials: "include"`.
2. **Validation:** backend validates the JWT on protected routes before allowing access (`AUTH-007`).
3. **Proactive refresh:** ~1 minute before access-token expiry, the frontend silently calls `POST /auth/refresh` (cookie credential), updates Zustand with the new access token, and reschedules. The user must not notice this.
4. **Reactive refresh (fallback):** when an authenticated request returns 401 because the access token expired, the API client performs a single-flight refresh-and-retry, transparent to the UI (`FE-005`). Access-token expiry alone must **not** clear Zustand or redirect to `/login`.
5. **Reuse detection:** if a refresh token that was already rotated out is presented again, the **entire token family is revoked** and the user must re-authenticate — this is a theft signal, not a normal error path.
6. **Logout:** explicit user action → `POST /auth/logout` → backend revokes the refresh session and clears the cookie → frontend clears Zustand → redirect to `/login` (`FE-006`). Do **not** clear auth from `useEffect` cleanup, `beforeunload`, `visibilitychange`, tab/window close, or route changes.
7. **Invalid refresh session only:** refresh returns 401 (missing/expired/revoked/reused cookie) → frontend clears Zustand and may redirect to login (`FE-006`). Network errors and 5xx must **not** clear auth.

## 4. Security Parameters (settled — do not rederive)

These were explicitly delegated to the delivery team by the client ("decide by yourself considering security") and are now fixed values, not open questions:

| Parameter | Value | ID |
|---|---|---|
| OTP expiry | 10 minutes | `AUTH-011` |
| OTP resend cooldown | 60 seconds | `AUTH-011` |
| OTP failed-attempt lockout | 5 attempts → 15-minute lockout | `AUTH-011` |
| OTP storage | Hashed, never plaintext | `AUTH-011` |
| Access token lifetime | 15 minutes | `AUTH-012` |
| Refresh token lifetime | **7 days**, rotated on every use (v1.4; was 30 days under the prior Zustand-held refresh model) | `AUTH-012` |
| Refresh token reuse detection | Whole token family revoked on reuse | `AUTH-012` |

## 5. Server-Side Session Model

`AUTH-010`: refresh tokens must be revocable server-side. This requires a store of issued/rotated refresh tokens **keyed by a token identifier, not the raw token** — see `Refresh Token / Session Record` in [`docs/database-design.md`](./database-design.md) (`DATA-003`), which also carries rotation lineage to support the reuse-detection rule above.

The browser-visible half of the session is the httpOnly `refresh_token` cookie (`Secure` outside development, `SameSite=Strict`, `Path=/`, Max-Age = refresh lifetime). Cookie-authenticated endpoints additionally enforce CSRF checks (`X-Requested-With` + Origin/Referer allow-list) — see [`docs/security.md`](./security.md) §4.

## 6. Frontend Token Management

| ID | Requirement |
|---|---|
| FE-001 | Auth state managed via Zustand. |
| FE-002 (v1.4) | Access token + user in Zustand (memory). Refresh token in httpOnly cookie only. Never `localStorage` / `sessionStorage` / Zustand `persist`. |
| FE-003 | Centralized in a single auth store/service — not duplicated across components. |
| FE-004 | Access token automatically attached to authenticated requests via a centralized API client. |
| FE-005 | Expired access token triggers silent refresh-and-retry (plus proactive refresh before expiry), transparent to the UI. |
| FE-006 | Invalid **refresh** session (401 from refresh) clears auth state and redirects to login. Explicit logout does the same. Access-token expiry, page refresh, tab/browser close, network blips, and 5xx must not. |
| FE-007 | Auth logic stays out of UI components where practical — UI never handles raw tokens. |

### 6.1 Session persistence & startup

The browser talks to FastAPI through a **same-origin Next.js rewrite** (`NEXT_PUBLIC_API_URL=/api/backend` → `BACKEND_URL`). The httpOnly refresh cookie is therefore first-party on the frontend origin. Do not call `http://localhost:8000` directly from the browser.

```
Application starts / page refreshes
      ↓
status = "idle"  (isAuthInitializing)
      ↓
bootstrapSession() [module single-flight] → POST /auth/refresh (cookie)
      ↓
Valid refresh session?
   ├── YES → access token + user → status = "authenticated"
   └── NO (401) → status = "unauthenticated" → guards may redirect to /login
```

Protected routes must **wait** while `status === "idle"`. Parallel `/auth/refresh` calls are forbidden (rotation race → false session kill under React Strict Mode).

Persistence matrix (refresh cookie still valid):

| Event | Expected result |
|---|---|
| Page refresh | Remains authenticated |
| Tab / window close + reopen | Remains authenticated |
| Browser restart | Remains authenticated |
| Access token expires | Silent refresh; user stays on current page |
| Explicit logout | Cleared; `/login` |
| Refresh cookie revoked / expired | Cleared; `/login` |
| API 500 / network error | Stay authenticated |

### 6.2 Zustand shape (implementation)

```
user
accessToken
accessTokenExpiresAt
status: "idle" | "authenticated" | "unauthenticated"
  ↔ isAuthInitializing = status === "idle"
  ↔ isAuthenticated     = status === "authenticated"
```

## 7. Roles

`AUTH-008`/`AUTH-009`: the User data model carries a `role` field. Phase 1 populates only `"user"`; this exists so an `"admin"` role can be introduced in Phase 2 (see `docs/brd.md` §4) without a schema rework. Role/permission enforcement beyond this reserved field is not otherwise specified for Phase 1, since there is only one functional role.

## 8. Residual Risk (ASM-001 — updated for v1.4)

The refresh token is no longer reachable from page JavaScript (httpOnly cookie), which closes the residual XSS exfiltration path that the earlier “both tokens in Zustand” model accepted. The short-lived access token still lives in memory and remains theoretically readable by a same-origin XSS payload for at most its 15-minute lifetime — mitigate with standard XSS hardening (CSP, output encoding, dependency hygiene) in [`docs/security.md`](./security.md).

## 9. Endpoints (summary — full contracts in api-specification.md)

| Endpoint | Purpose |
|---|---|
| `POST /auth/register` | Step 1 of signup (email + password) |
| `POST /auth/login` | Step 1 of login (email + password) |
| `POST /auth/otp/verify` | Step 2 of both flows (OTP submission) — sets refresh cookie |
| `POST /auth/otp/resend` | Re-send OTP, subject to the 60s cooldown |
| `POST /auth/refresh` | Cookie credential → new access token; rotates refresh cookie |
| `POST /auth/logout` | Revoke current refresh session; clear cookie |
| `GET /auth/me` | Current user (used after refresh on startup) |

Full request/response shapes: [`docs/api-specification.md`](./api-specification.md) §Authentication.

## 10. Open Items

None outstanding for authentication itself — `OQ-001`, `OQ-003`, `OQ-005`, and `OQ-009` are resolved (v1.4 revises `OQ-009`/`FE-002` to httpOnly refresh cookies). The only related open item is the **specific OTP email vendor** (`NFR-012` — channel is confirmed as email, provider TBD, non-blocking); see `docs/architecture.md` §7.

## 11. Related Documents

- [`docs/architecture.md`](./architecture.md) §3 — the mandated layering this flow implements.
- [`docs/security.md`](./security.md) — broader security posture, including this flow's trade-offs.
- [`docs/database-design.md`](./database-design.md) — `User`, `OTP Record`, `Refresh Token / Session Record` entities.
- [`docs/api-specification.md`](./api-specification.md) — endpoint contracts.
