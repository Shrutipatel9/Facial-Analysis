# Security

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`AUTH-010`–`AUTH-012`, `ASM-001`, `BR-005`/`CON-006`). This document covers security posture **beyond** the auth flow's own mechanics, which live in [`docs/authentication.md`](./authentication.md) — read that first; this file does not repeat token/OTP lifetimes.

**Status:** Draft, derived from `client_requirements.md` v1.1.

---

## 1. Scope of This Document

Security concerns that cut across modules, rather than living inside any one module's `plans.md`:
- Credential and secret handling
- Token storage trade-offs (cross-reference, not duplicate, of `docs/authentication.md` §8)
- Photo validation as a safety gate, not just a UX feature
- Third-party data exposure
- What is explicitly **not** covered yet (Phase 2 / deferred)

## 2. Credential & Secret Handling

| Item | Requirement |
|---|---|
| Passwords | Hashed at rest (never stored/logged in plaintext). Specific algorithm not client-specified — **[Recommendation]**: a modern adaptive hash (e.g. bcrypt/argon2) via a maintained library, decided during implementation. |
| OTP values | Hashed at rest, never plaintext (`AUTH-011`). |
| Refresh tokens | Stored server-side by a token identifier, not the raw token (`AUTH-010`) — see `docs/authentication.md` §5. |
| API keys (OpenAI, Stripe, email provider) | Backend-only environment configuration; must never reach the frontend bundle or client-visible responses. Not explicitly stated by the client but required by the third-party integrations in `docs/architecture.md` §1 — **[Assumption]**. |

## 3. Token Storage Trade-off (cross-reference)

The client explicitly chose client-side JS store token storage (originally Redux, now Zustand as of v1.2 — see `NFR-006`) over `localStorage` (`FE-002`) and, earlier, over `httpOnly` cookies (`OQ-009`, resolved). The residual XSS exposure this carries, and why it's an accepted trade-off rather than an oversight, is documented in [`docs/authentication.md`](./authentication.md) §8 (`ASM-001`). The mitigations that matter here are standard web hardening, not token-storage changes:

- Content-Security-Policy (CSP) restricting script sources.
- Consistent output encoding to prevent script injection into rendered content.
- Dependency hygiene (auditing frontend/backend dependencies for known vulnerabilities) — relevant given the number of third-party packages (Stripe.js, MediaPipe, etc.).

## 4. Photo Validation as a Security/Quality Gate (BR-005, CON-006)

Because Phase 1 auto-publishes reports with no admin review (`BR-002`), enforced photo validation is not just a UX nicety — it is the only safety gate between an unusable/adversarial input and a paying user's report (`BR-004`). Recommended checks (thresholds deferred to development, `ASM-002`):

- Exactly one face detected.
- Face occupies a reasonable proportion of the frame.
- No obvious occlusion over eyes/mouth (glasses/hat).
- Minimum resolution.
- Basic brightness/exposure check.

**Do not relax this gate to "checklist only" even under implementation-time pressure** — that would reintroduce the exact risk `BR-004`/`CON-006` exist to prevent (a low-quality or adversarial input being auto-published straight to a paying user with no human in the loop).

## 5. Third-Party Data Exposure

| Third party | Data sent | Note |
|---|---|---|
| OpenAI | Facial measurements + questionnaire answers (`FR-008`) | Questionnaire includes sensitive self-perception/medical-adjacent content (`FR-003`) — treat this as sensitive data in transit/at rest even though the client has not specified a formal data-retention policy yet (Phase 2, see §6). |
| Stripe | Payment details | Standard PCI-scope reduction applies — the backend should not handle raw card data directly; use Stripe's client-side tokenization/hosted flows. Not explicitly stated by the client — **[Recommendation]**, standard practice for the stated Stripe integration (`NFR-009`). |
| Email/OTP provider | User email address, OTP code | Vendor TBD (`NFR-012`). |

## 6. Explicitly Not Covered Yet

- **Formal data-retention/privacy policy** — Phase 2 (`client_requirements.md` §2.2). Until defined, do not assume a specific retention period for photos, questionnaire answers, or reports; avoid hardcoding deletion logic that would conflict with a policy not yet written.
- **Admin-side security** (role-based access beyond the reserved `role` field) — Phase 2, once the admin panel exists.

## 7. Open Items

| Item | Status |
|---|---|
| Photo validation exact thresholds | Deferred to development (`ASM-002`) — document final values here once set, per `client_requirements.md`'s own instruction (Section 11). |
| Password hashing algorithm choice | Not client-specified — **[Recommendation]**, decide during `authentication` module implementation and record the decision here. |
| Data retention policy | Explicitly Phase 2 — do not build retention/deletion logic ahead of it. |

## 8. Related Documents

- [`docs/authentication.md`](./authentication.md) — token/OTP mechanics and the storage trade-off this document references.
- [`docs/architecture.md`](./architecture.md) §6 — non-functional considerations this document elaborates on.
- [`docs/testing-strategy.md`](./testing-strategy.md) — how the lockout, rotation/reuse-detection, and photo-validation gates are verified.
