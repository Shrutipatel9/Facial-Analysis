# Architecture

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`NFR-*`, Section 5.3, `WF-002`). Auth-internal detail lives in [`docs/authentication.md`](./authentication.md) and is not repeated here beyond the layering contract. Data shapes live in [`docs/database-design.md`](./database-design.md); endpoint contracts in [`docs/api-specification.md`](./api-specification.md).

**Status:** Draft, derived from `client_requirements.md` **v1.4**. Describes the target architecture. The `authentication` module is implemented (custom JWT/OTP, httpOnly refresh cookie, Zustand access-token store, AuthHydrator session restore). Later Phase 1 modules build on that foundation.

> **v1.3 resolves `ASM-004`.** v1.2 had briefly assumed the frontend and backend would consolidate into one Next.js application. The client has confirmed this was wrong: **frontend and backend are two separate applications**, communicating over HTTP. The backend reverts to **Python + FastAPI** (with SQLAlchemy/Alembic, also reverted from v1.2's Prisma) — Next.js is frontend-only in this project. PostgreSQL (vendor-neutral) and Zustand (replacing Redux) from v1.2 are unaffected by this revision.

---

## 1. Technology Stack

| Layer | Choice | Requirement ID |
|---|---|---|
| Frontend | **Next.js (TypeScript, App Router)** — separate application, UI only | `NFR-005` |
| Backend | **Python + FastAPI** — separate application, REST API only | `NFR-001` |
| Database | **PostgreSQL** — vendor-neutral; hosting provider not yet decided (`NFR-010`) | `NFR-002` |
| Migrations | **Alembic** | `NFR-003` |
| ORM | **SQLAlchemy** | `NFR-004` |
| Frontend state | **Zustand**, at minimum for authentication state | `NFR-006` |
| Facial analysis | MediaPipe + OpenCV, built from scratch, runs in-process in the Python backend (no cross-language process boundary needed — see note below) | `NFR-007` |
| Narrative/recommendation generation | OpenAI (Vision + GPT), called from the Python backend | `NFR-008` |
| Payments | Stripe (Phase 1); PayPal deferred to Phase 2 | `NFR-009` |
| Hosting | **Undecided, not currently needed** — do not assume any platform | `NFR-010`/`CON-007` |

`NFR-011` (clean, modular, well-documented code) is a cross-cutting requirement, not a component — see `docs/brd.md` §2 (`BC-005`) for why it exists and this document's §5 for how module boundaries support it.

**Superseded (v1.1 → v1.2 → v1.3):** v1.2 briefly moved the backend to TypeScript/Next.js/Prisma under a single-app consolidation reading. v1.3 reverts the backend to Python/FastAPI/SQLAlchemy/Alembic (its v1.1 values) now that the client confirmed two separate apps — Next.js is frontend-only. Supabase (dropped in v1.2) and Redux (replaced by Zustand in v1.2) remain superseded; see `client_requirements.md` change log for the full history.

**MediaPipe/OpenCV note (resolved in v1.3):** v1.2 had flagged an open question about running Python-native MediaPipe/OpenCV from a TypeScript/Next.js app (would have needed a separate process/service boundary). With the backend confirmed as Python/FastAPI, this concern is moot — MediaPipe/OpenCV run in-process in the same Python backend as everything else, per the original v1.1 design intent.

## 2. High-Level Component Diagram

```
   ┌─────────────────────────┐
   │        Browser           │
   └────┬─────────────────┬───┘
        │ HTTPS (pages)    │ HTTPS/CORS (REST API calls)
        ▼                  ▼
┌───────────────┐   ┌──────────────────────────┐
│  Frontend       │   │  Backend                  │
│  Next.js (TS)   │──▶│  FastAPI (Python)          │
│  App Router     │   │  SQLAlchemy + Alembic       │
│  UI only         │   │  JWT/OTP services            │
└───────────────┘   └──┬──────────┬──────────┬───┘
                        │          │          │
              ┌─────────┘          │          └─────────┐
              ▼                    ▼                     ▼
   ┌────────────────┐   ┌──────────────────┐   ┌──────────────────┐
   │  PostgreSQL      │   │ MediaPipe/OpenCV  │   │  OpenAI (Vision/  │
   │  (data only, not  │   │ (in-process,       │   │  GPT) — narrative │
   │   auth; hosting    │   │  Python-native)     │   │  generation       │
   │   provider TBD)    │   └──────────────────┘   └──────────────────┘
   └────────────────┘
              │
              ▼
   ┌────────────────┐        ┌──────────────────┐
   │ Stripe (payments)│        │ Email/OTP provider│
   │                  │        │ (vendor TBD)       │
   └────────────────┘        └──────────────────┘
```

The Frontend calls the Backend's REST API directly from the browser (client-side `fetch`, via the centralized API client in §3) — there is no server-side proxy layer between them. OpenAI, Stripe, and the OTP email provider are external HTTP services called from the FastAPI backend; the browser never calls them directly. CORS on the FastAPI side must explicitly allow the Next.js dev/prod origin(s).

## 3. Required Layering — Authentication (Section 5.3, non-negotiable)

This exact layering was specified directly by the client and must be preserved in implementation — only the store library name changed in v1.2 (Redux → Zustand); the contract itself did not. It now spans two applications rather than one:

```
UI → Zustand Auth Store → API Client → Backend Auth APIs → JWT/OTP Services
   |________ Frontend (Next.js) ________|  |___ Backend (FastAPI) ___|
```

| Layer | Responsibility | Must NOT do |
|---|---|---|
| UI | Presentational components (React, Next.js) | Call auth APIs or touch tokens directly (`FE-007`) |
| Zustand Auth Store | Single source of truth for auth state (user, access token, `status` / initializing flag). Refresh token is **not** stored here (`FE-002` v1.4) | Be duplicated per-component (`FE-003`); ever be wrapped in Zustand's `persist` middleware (would silently reintroduce `localStorage` / `sessionStorage`) |
| API Client | Centralized HTTP client in the Next.js app; attaches the access token via `Authorization`, sends cookies with `credentials: "include"`, handles proactive refresh + 401 refresh-and-retry (single-flight, see `docs/authentication.md`) | Live inside UI components; clear auth on network/5xx |
| Backend Auth APIs | FastAPI endpoints (separate origin): register, login, OTP verify, refresh, logout, `/auth/me`, and JWT dependencies; sets/clears the httpOnly refresh cookie | Delegate identity to a third party (`AUTH-005`) |
| JWT/OTP Services | Backend-internal Python service modules for token issuance/validation and OTP generation/verification/email delivery | Live inside route handler functions directly (must be decoupled into importable service modules) |

Full flow detail (state machine, lifetimes, rotation/reuse detection, persistence): [`docs/authentication.md`](./authentication.md).

**Zustand vs. Redux — why this doesn't change the contract.** Redux requires a store provider wrapping the component tree and action/reducer boilerplate; Zustand exposes a plain hook (`useAuthStore()`) with no provider required. This is a delivery-team implementation note, not a client requirement — the client's actual requirement is the layering contract and the "not `localStorage`" rule, both preserved.

**Two-app consequence — CORS with credentials.** Because the Frontend and Backend are separate origins, the API Client's requests are cross-origin. The access token travels in `Authorization: Bearer`; the refresh token travels as an httpOnly cookie. FastAPI must use `allow_credentials=True` with an explicit `CORS_ORIGINS` allow-list (never `*` with credentials).

## 4. Data Flow Across the Product Workflow

See [`docs/prd.md`](./prd.md) §4 for the user-facing workflow (`WF-001`). Architecturally, each step maps to a backend module boundary (a FastAPI router + SQLAlchemy models + service functions):

| Workflow step | Backend module | Persists to | External call |
|---|---|---|---|
| Auth (signup/login/OTP) | `authentication` | User, OTP Record, Refresh Token/Session | Email/OTP provider |
| Onboarding questionnaire | `onboarding-questionnaire` | Questionnaire Response | — |
| Photo upload + validation | `photo-upload-validation` | Photo (+ validation result) | — |
| AI processing | `facial-analysis-engine` | Facial Analysis Result | OpenAI |
| Report assembly | `report-generation` | Report | — |
| Payment | `payment` | Payment | Stripe |
| Dashboard | `user-dashboard` | reads Report, Payment | — |

This table is the architectural rationale behind the module split used in [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) and the per-module plans under `D:\zzz\`.

## 5. Modularity & Maintainability (NFR-011, BC-005)

Because the client's own team will extend this codebase post-handoff using AI-assisted tools, module boundaries should be drawn along the table in §4 — one FastAPI router + SQLAlchemy-model-set per workflow step — rather than by technical layer alone. This keeps each module independently understandable: a future contributor working on, say, `report-generation` should not need to read `payment` internals to make a correct change.

Concretely, this means:
- Routers stay thin; business logic lives in per-module service functions (mirrors the JWT/OTP Services separation mandated for auth, generalized to every module).
- SQLAlchemy models are organized per module (`app/models/<module>.py`), matching the entities in `docs/database-design.md`; Alembic migrations are reviewed (not blindly accepted) before applying.
- Cross-module coupling is limited to what §4 implies (e.g. `report-generation` reads `Facial Analysis Result` and `Questionnaire Response`, but does not reach into `authentication` internals beyond the standard `get_current_user` dependency).
- The same principle applies on the frontend: each module's UI lives under its own route group/feature folder, reading only the Zustand stores and API client functions it needs.

## 6. Non-Functional Considerations

| Concern | Note |
|---|---|
| Security | See [`docs/security.md`](./security.md) for the full posture (token/OTP handling, XSS trade-off, photo-validation-as-safety-gate). |
| Hosting | Explicitly undecided (`NFR-010`/`CON-007`). Two separate deployable apps (a Next.js app, a FastAPI app) is a common, broadly portable shape — avoid provider-specific primitives without flagging them as swappable. |
| Third-party cost ownership | OpenAI/Stripe/PostgreSQL-hosting/email provider usage costs are the client's responsibility (`BR-006`), not an architectural constraint but relevant to any usage-based design choice (e.g. how aggressively OpenAI is called). |
| Configurability | Report price (`OQ-002`) and photo-validation thresholds (`ASM-002`) must be configuration values, not hardcoded constants — both are explicitly undecided/deferred by the client. |
| CORS | The FastAPI backend's allowed-origins list must be environment-configurable (dev origin vs. eventual production origin), not hardcoded to `localhost`. |

## 7. Open Questions / Assumptions Affecting Architecture

| ID | Item | Status |
|---|---|---|
| ASM-004 | Frontend+backend consolidation | **Resolved in v1.3** — confirmed as two separate apps (Next.js frontend, FastAPI backend). |
| ASM-002 | Photo validation thresholds | Deferred to development time — architecture must make these configurable, not hardcode a guess now. |
| OQ-002 | Report price | Deferred — must be configurable. |
| NFR-010/CON-007 | Hosting platform | Undecided — do not couple architecture to a specific host's features. |
| — | Specific OTP email provider (SendGrid/SES/Postmark/etc.) | To be picked during development (`NFR-012`); architecture should isolate this behind an OTP-delivery interface so the choice is swappable. |

## 8. Related Documents

- [`docs/authentication.md`](./authentication.md) — full auth flow, token/OTP lifecycle.
- [`docs/security.md`](./security.md) — security posture and trade-offs.
- [`docs/database-design.md`](./database-design.md) — schema realizing the entities in §4 (SQLAlchemy).
- [`docs/api-specification.md`](./api-specification.md) — endpoint contracts realizing this architecture (FastAPI).
- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — how these modules are sequenced.
