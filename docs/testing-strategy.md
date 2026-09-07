# Testing Strategy

**Source of truth:** [`client_requirements.md`](./client_requirements.md). Per that document (Section 13): "Every `FR-*`/`AUTH-*`/`BR-*` should map to at least one test case when this doc is written." This document defines the testing **approach and category-level mapping**; concrete test cases are written per module in each `plans.md` under `D:\zzz\`, not enumerated here.

**Status:** Draft. No test suite exists yet in `Backend/` or `Frontend/` as of this writing (see repository root `CLAUDE.md`).

---

## 1. Testing Levels

| Level | Scope | Applies to |
|---|---|---|
| Unit | Individual functions/services (e.g. OTP hashing, token rotation logic, photo-validation checks, report-section assembly) | All backend modules |
| Integration | A module's API endpoints against a real (test) database | All backend modules with persistence |
| Component/UI | Individual React components and Zustand stores in isolation | Frontend modules |
| End-to-end (E2E) | Full `WF-001` journey through a running frontend + backend | Cross-module |
| Security-specific | Auth abuse paths (lockout, reuse detection), payment-gate bypass attempts, photo-validation bypass attempts | `authentication`, `payment`, `photo-upload-validation` |

## 2. Requirement-to-Test-Category Mapping

This is a category-level mapping, not literal test cases — each row expands into concrete cases inside the relevant module's `plans.md`.

| Requirement area | Test categories required |
|---|---|
| `FR-001` (landing page) | Component: CTA renders and routes to signup. |
| `AUTH-001`–`AUTH-012`, `WF-002` | Integration: full signup/login two-step flow (happy path); OTP expiry; OTP resend cooldown; 5-failed-attempt lockout; access-token expiry + silent refresh (proactive and 401→retry); refresh-token rotation via httpOnly cookie; **refresh-token reuse → whole family revoked** (do not skip); logout revocation + cookie clear; startup session restore; network/5xx must not clear auth. |
| `FE-001`–`FE-007` | Component/unit: Zustand auth store state transitions (`idle` / authenticated / unauthenticated); API client attaches token and single-flight refreshes; protected routes wait while initializing; UI never handles raw tokens (lint boundary where practical). |
| `FR-003`, `FR-004`, `BR-003` | Integration: questionnaire submission rejected server-side when `disclaimer_accepted` is false, even if the client bypasses the UI gate. |
| `FR-005`, `FR-006`, `BR-005` | Integration: each validation check (face count, frame proportion, occlusion, resolution, brightness) individually triggers a rejection with the correct reason; a fully-compliant photo set passes. |
| `BR-004` | Integration: analysis pipeline cannot be triggered from a photo set with `validation_status = failed`. |
| `FR-007`, `FR-008` | Integration: analysis output includes measurements for all features; narrative generation call includes both measurements and questionnaire answers (assert both are present in the OpenAI request payload, not just one). |
| `FR-009`–`FR-012` | Unit/integration: generated report always contains all 11 features (`BR-008`) each with narrative + before/after + summary callout; report-level intro/preamble/limitations/recommendations sections are present. |
| `FR-013` | Integration: PDF export succeeds and is only retrievable post-payment (see `BR-001` row below — same gate). |
| `FR-014`, `BR-002` | Integration: report `publish_state` is set immediately on generation, no intermediate review state blocks availability in Phase 1. |
| `FR-015`, `BR-001` | Integration/security: full report content and PDF endpoints return teaser-only (or 403) for an unpaid report, even with a direct authenticated request bypassing the UI. |
| `FR-016`, `OQ-002` | Unit: checkout uses the configured price value, not a hardcoded literal — test should fail if price is inlined. |
| `FR-017` | Integration: dashboard aggregation reflects current report/payment state after each workflow transition. |
| `AUTH-009` (role field) | Unit: `role` defaults to `"user"` and is present on every created User record, even though no admin role exists yet. |

## 3. Security-Specific Testing (cross-reference docs/security.md)

- OTP and refresh-token values are never asserted against in test output/logs in plaintext — tests should check hashes/behavior, not print secrets.
- Reuse-detection test (§2 above) is the single highest-value security test in the whole suite, since it's the one mechanism protecting against a stolen refresh token being used silently — treat a failure here as a release blocker, not a flaky test to skip.
- Payment-gate bypass attempts (§2, `BR-001` row) should be tested as a direct authenticated API call, not only via UI interaction, since `BR-001` is a business rule that must hold regardless of client.

## 4. Environments

- **Test database:** a dedicated Postgres instance/schema, separate from the one used for development or production data — not explicitly specified by the client; **[Recommendation]** to avoid test runs mutating real data.
- **External services in tests:** OpenAI, Stripe, and the email/OTP provider should be mocked/stubbed in unit and integration tests; a smaller set of manual or sandbox-mode (e.g. Stripe test mode) checks can cover real integration behavior before release. Not specified by the client — **[Recommendation]**, standard practice given `BR-006` (third-party costs are the client's responsibility — tests should not incur avoidable usage costs).

## 5. Out of Scope for Phase 1 Testing

No admin-panel, email-notification, PayPal, tracking-pixel, AI-visual-feature, or AI-chat test coverage — those modules don't exist yet (see `docs/brd.md` §3.2).

## 6. Open Items

| Item | Status |
|---|---|
| Photo-validation exact thresholds | Deferred (`ASM-002`) — test cases for validation boundaries can only be finalized once thresholds are set; write them against configuration values, not hardcoded numbers. |
| Test framework choice | Not specified by the client — **[Recommendation]**: `pytest` (+ `pytest-asyncio`, `httpx` test client) for the FastAPI backend; Vitest/RTL for frontend unit/component tests, Playwright for E2E. (v1.2 had briefly dropped pytest under a since-reverted TypeScript-backend assumption; v1.3 restores it now that the backend is confirmed Python.) |

## 7. Related Documents

- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — per-phase testing requirements and acceptance criteria.
- [`docs/security.md`](./security.md) — the security posture these tests verify.
- Each module's `plans.md` under `D:\zzz\` — concrete test cases per module.
