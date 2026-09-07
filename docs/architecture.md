# Architecture

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`NFR-*`, Section 5.3, `WF-002`). Auth-internal detail lives in [`docs/authentication.md`](./authentication.md) and is not repeated here beyond the layering contract. Data shapes live in [`docs/database-design.md`](./database-design.md); endpoint contracts in [`docs/api-specification.md`](./api-specification.md).

**Status:** Draft, derived from `client_requirements.md` v1.2. Describes the target architecture — as of this writing, `Backend/` and `Frontend/` on disk still reflect the **superseded v1.1 stack** (Python/FastAPI, Vite/React) and have not yet been migrated to the stack below (see repository root `CLAUDE.md`).

> **v1.2 stack change.** The client requested a tech-stack revision: TypeScript + Next.js backend, PostgreSQL (vendor-neutral, Supabase dropped), and a lighter frontend store than Redux. Because Next.js is a full-stack framework rather than a backend-only tool, this document treats the frontend and backend as **consolidated into one Next.js application** — this reading is flagged as `ASM-004` in `client_requirements.md` (delivery-team interpretation, not yet explicitly confirmed by the client). If the client intended to keep a separate frontend app calling a Next.js-only API, revisit every folder-structure and "single app" statement below.

---

## 1. Technology Stack

| Layer | Choice | Requirement ID |
|---|---|---|
| Application framework | **Next.js (TypeScript)** — full-stack: UI via React Server/Client Components, API via Route Handlers | `NFR-001`, `NFR-005` |
| Database | **PostgreSQL** — vendor-neutral; hosting provider not yet decided (`NFR-010`) | `NFR-002` |
| Migrations | **Prisma Migrate** | `NFR-003` |
| ORM | **Prisma** | `NFR-004` |
| Frontend state | **Zustand**, at minimum for authentication state | `NFR-006` |
| Facial analysis | MediaPipe + OpenCV, built from scratch (no existing engine reused) | `NFR-007` |
| Narrative/recommendation generation | OpenAI (Vision + GPT) | `NFR-008` |
| Payments | Stripe (Phase 1); PayPal deferred to Phase 2 | `NFR-009` |
| Hosting | **Undecided, not currently needed** — do not assume any platform | `NFR-010`/`CON-007` |

`NFR-011` (clean, modular, well-documented code) is a cross-cutting requirement, not a component — see `docs/brd.md` §2 (`BC-005`) for why it exists and this document's §5 for how module boundaries support it.

**Superseded (v1.1 → v1.2):** Python + FastAPI backend, SQLAlchemy ORM, Alembic migrations, Supabase-hosted Postgres, separate Vite + React frontend, Redux/Redux Toolkit. None of these should appear in new implementation work; see `client_requirements.md` change log (v1.2) for the full rationale.

**MediaPipe/OpenCV note:** these remain Python-native libraries (`NFR-007` doesn't specify a language binding, but MediaPipe/OpenCV's most mature APIs are Python/C++, not Node.js). Since the application layer is now TypeScript/Next.js, the CV measurement step will likely need to run as a separate process/service invoked from Next.js (e.g. a Python microservice or subprocess called from a Route Handler) rather than in-process in the same runtime as the rest of the app. **This is a new architectural decision introduced by the v1.2 stack change, not resolved by the client** — flagged as an open item in §7 and in the `facial-analysis-engine` module plan.

## 2. High-Level Component Diagram

```
                    ┌─────────────────────────────┐
                    │         Browser              │
                    │  (Next.js React UI, served    │
                    │   by the same app below)       │
                    └────────────┬─────────────────┘
                                 │ HTTPS
                                 ▼
                    ┌─────────────────────────────┐
                    │   Next.js application         │
                    │   (TypeScript)                 │
                    │   UI (Server/Client Components)│
                    │   + API (Route Handlers)       │
                    │   + Prisma ORM                 │
                    └───┬─────────┬─────────┬───────┘
                        │         │         │
              ┌─────────┘         │         └─────────┐
              ▼                   ▼                    ▼
   ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  PostgreSQL      │  │ MediaPipe/OpenCV  │  │  OpenAI (Vision/  │
   │  (data only, not  │  │ (CV measurement —  │  │  GPT) — narrative │
   │   auth; hosting    │  │  see §1 note on     │  │  generation       │
   │   provider TBD)    │  │  process boundary)  │  │                    │
   └────────────────┘  └──────────────────┘  └──────────────────┘
              │
              ▼
   ┌────────────────┐        ┌──────────────────┐
   │ Stripe (payments)│        │ Email/OTP provider│
   │                  │        │ (vendor TBD)       │
   └────────────────┘        └──────────────────┘
```

OpenAI, Stripe, and the OTP email provider are external HTTP services called from Next.js Route Handlers; the browser never calls them directly. The CV step's process boundary is called out separately per the §1 note.

## 3. Required Layering — Authentication (Section 5.3, non-negotiable)

This exact layering was specified directly by the client and must be preserved in implementation — only the store library name changed in v1.2 (Redux → Zustand); the contract itself did not:

```
UI → Zustand Auth Store → API Client → Backend Auth APIs → JWT/OTP Services
```

| Layer | Responsibility | Must NOT do |
|---|---|---|
| UI | Presentational components (React, within the Next.js app) | Call auth APIs or touch tokens directly (`FE-007`) |
| Zustand Auth Store | Single source of truth for auth state (user, both tokens, auth status); confirmed token storage location (`FE-002`) | Be duplicated per-component (`FE-003`) |
| API Client | Centralized HTTP client (e.g. a typed fetch wrapper); reads tokens from the Zustand store, attaches them to requests, handles refresh-on-401 | Live inside UI components |
| Backend Auth APIs | Next.js Route Handlers under an API route segment: register, login, OTP verify, refresh, logout, and protected-route middleware/helpers for JWT validation | Delegate identity to a third party (`AUTH-005`) |
| JWT/OTP Services | Backend-internal TypeScript modules for token issuance/validation and OTP generation/verification/email delivery | Live inside route handler files directly (must be decoupled into importable service modules) |

Full flow detail (state machine, lifetimes, rotation/reuse detection): [`docs/authentication.md`](./authentication.md).

**Zustand vs. Redux — why this doesn't change the contract.** Redux requires a store provider wrapping the component tree and action/reducer boilerplate; Zustand exposes a plain hook (`useAuthStore()`) with no provider required, which fits Next.js's mix of Server and Client Components more simply (only Client Components read the store; Server Components never do, since server-rendered code has no access to the browser-side, in-memory Zustand state — server-side logic that needs the current user identity does so via the request's own JWT validation, not by reading the Zustand store). This is a delivery-team implementation note, not a client requirement — the client's actual requirement is the layering contract and the "not `localStorage`" rule, both preserved.

## 4. Data Flow Across the Product Workflow

See [`docs/prd.md`](./prd.md) §4 for the user-facing workflow (`WF-001`). Architecturally, each step maps to a backend module boundary (a route-handler group + Prisma models + service functions, following the Next.js App Router's route-group conventions):

| Workflow step | Backend module | Persists to | External call |
|---|---|---|---|
| Auth (signup/login/OTP) | `authentication` | User, OTP Record, Refresh Token/Session | Email/OTP provider |
| Onboarding questionnaire | `onboarding-questionnaire` | Questionnaire Response | — |
| Photo upload + validation | `photo-upload-validation` | Photo (+ validation result) | — |
| AI processing | `facial-analysis-engine` | Facial Analysis Result | OpenAI (+ CV process, see §1 note) |
| Report assembly | `report-generation` | Report | — |
| Payment | `payment` | Payment | Stripe |
| Dashboard | `user-dashboard` | reads Report, Payment | — |

This table is the architectural rationale behind the module split used in [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) and the per-module plans under `D:\zzz\`.

## 5. Modularity & Maintainability (NFR-011, BC-005)

Because the client's own team will extend this codebase post-handoff using AI-assisted tools, module boundaries should be drawn along the table in §4 — one route-group + Prisma-model-set per workflow step — rather than by technical layer alone. This keeps each module independently understandable regardless of the framework change: a future contributor working on, say, `report-generation` should not need to read `payment` internals to make a correct change.

Concretely, this means:
- Route Handlers stay thin; business logic lives in per-module service functions (mirrors the JWT/OTP Services separation mandated for auth, generalized to every module) — this principle is unchanged by the FastAPI→Next.js switch, only the file/route convention differs.
- Prisma schema is organized so each module's models are easy to locate (e.g. grouped by comment section in `schema.prisma`, or split via Prisma's multi-file schema support if the project's Prisma version supports it), matching the entities in `docs/database-design.md`.
- Cross-module coupling is limited to what §4 implies (e.g. `report-generation` reads `Facial Analysis Result` and `Questionnaire Response`, but does not reach into `authentication` internals beyond the standard "current user" helper).

## 6. Non-Functional Considerations

| Concern | Note |
|---|---|
| Security | See [`docs/security.md`](./security.md) for the full posture (token/OTP handling, XSS trade-off, photo-validation-as-safety-gate). |
| Hosting | Explicitly undecided (`NFR-010`/`CON-007`). A consolidated Next.js app is broadly portable across hosting styles (Node server, serverless, or edge runtimes depending on provider), so this doesn't foreclose the hosting decision — but avoid provider-specific primitives (e.g. a specific platform's cron/queue product) without flagging it as a swappable choice. |
| Third-party cost ownership | OpenAI/Stripe/PostgreSQL-hosting/email provider usage costs are the client's responsibility (`BR-006`), not an architectural constraint but relevant to any usage-based design choice (e.g. how aggressively OpenAI is called). |
| Configurability | Report price (`OQ-002`) and photo-validation thresholds (`ASM-002`) must be configuration values, not hardcoded constants — both are explicitly undecided/deferred by the client. |

## 7. Open Questions / Assumptions Affecting Architecture

| ID | Item | Status |
|---|---|---|
| ASM-004 | Frontend+backend consolidation into one Next.js app | Delivery-team interpretation of a brief client instruction, **not explicitly confirmed** — verify with the client; if wrong, this document's "single app" framing needs revision. |
| — (new, v1.2) | How MediaPipe/OpenCV (Python-native) integrates with a TypeScript/Next.js app | Not resolved by the client — likely a separate process/service boundary (see §1 note); decide during `facial-analysis-engine` module implementation. |
| ASM-002 | Photo validation thresholds | Deferred to development time — architecture must make these configurable, not hardcode a guess now. |
| OQ-002 | Report price | Deferred — must be configurable. |
| NFR-010/CON-007 | Hosting platform | Undecided — do not couple architecture to a specific host's features. |
| — | Specific OTP email provider (SendGrid/SES/Postmark/etc.) | To be picked during development (`NFR-012`); architecture should isolate this behind an OTP-delivery interface so the choice is swappable. |

## 8. Related Documents

- [`docs/authentication.md`](./authentication.md) — full auth flow, token/OTP lifecycle.
- [`docs/security.md`](./security.md) — security posture and trade-offs.
- [`docs/database-design.md`](./database-design.md) — schema realizing the entities in §4 (Prisma).
- [`docs/api-specification.md`](./api-specification.md) — endpoint contracts realizing this architecture (Next.js Route Handlers).
- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — how these modules are sequenced.
