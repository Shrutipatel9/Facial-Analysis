# Architecture

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`NFR-*`, Section 5.3, `WF-002`). Auth-internal detail lives in [`docs/authentication.md`](./authentication.md) and is not repeated here beyond the layering contract. Data shapes live in [`docs/database-design.md`](./database-design.md); endpoint contracts in [`docs/api-specification.md`](./api-specification.md).

**Status:** Draft, derived from `client_requirements.md` v1.1. Describes the target architecture — as of this writing, `Backend/` and `Frontend/` contain only default scaffolding (see repository root `CLAUDE.md`).

---

## 1. Technology Stack

| Layer | Choice | Requirement ID |
|---|---|---|
| Backend framework | Python + FastAPI | `NFR-001` |
| Database | Supabase-hosted Postgres — **strictly** managed Postgres, never auth (`CON-002`) | `NFR-002` |
| Migrations | Alembic | `NFR-003` |
| ORM | SQLAlchemy | `NFR-004` |
| Frontend framework | React + Vite (Next.js from early pre-negotiation materials is superseded) | `NFR-005` |
| Frontend state | Redux / Redux Toolkit, at minimum for auth state | `NFR-006` |
| Facial analysis | MediaPipe + OpenCV, built from scratch (no existing engine reused) | `NFR-007` |
| Narrative/recommendation generation | OpenAI (Vision + GPT) | `NFR-008` |
| Payments | Stripe (Phase 1); PayPal deferred to Phase 2 | `NFR-009` |
| Hosting | **Undecided, not currently needed** — do not assume any platform | `NFR-010`/`CON-007` |

`NFR-011` (clean, modular, well-documented code) is a cross-cutting requirement, not a component — see `docs/brd.md` §2 (`BC-005`) for why it exists and this document's §5 for how module boundaries support it.

## 2. High-Level Component Diagram

```
                    ┌─────────────────────────┐
                    │        Browser           │
                    │  React + Vite frontend   │
                    └────────────┬─────────────┘
                                 │ HTTPS (JSON)
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI backend     │
                    │  (SQLAlchemy + Alembic)  │
                    └───┬─────────┬─────────┬──┘
                        │         │         │
              ┌─────────┘         │         └─────────┐
              ▼                   ▼                    ▼
   ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │ Supabase Postgres│  │ MediaPipe/OpenCV │  │  OpenAI (Vision/  │
   │ (data only, not  │  │ (in-process CV   │  │  GPT) — narrative │
   │  auth)           │  │  library, local) │  │  generation       │
   └────────────────┘  └──────────────────┘  └──────────────────┘
              │
              ▼
   ┌────────────────┐        ┌──────────────────┐
   │ Stripe (payments)│        │ Email/OTP provider│
   │                  │        │ (vendor TBD)       │
   └────────────────┘        └──────────────────┘
```

MediaPipe/OpenCV run in-process inside the backend (local CV libraries, not third-party services — see `client_requirements.md` Section 3). OpenAI, Stripe, and the OTP email provider are external HTTP services called by the backend; the frontend never calls them directly.

## 3. Required Layering — Authentication (Section 5.3, non-negotiable)

This exact layering was specified directly by the client and must be preserved in implementation:

```
UI → Redux Auth Store → API Client → Backend Auth APIs → JWT/OTP Services
```

| Layer | Responsibility | Must NOT do |
|---|---|---|
| UI | Presentational components | Call auth APIs or touch tokens directly (`FE-007`) |
| Redux Auth Store | Single source of truth for auth state (user, both tokens, auth status); confirmed token storage location (`FE-002`) | Be duplicated per-component (`FE-003`) |
| API Client | Centralized HTTP client; reads tokens from Redux, attaches them to requests, handles refresh-on-401 | Live inside UI components |
| Backend Auth APIs | FastAPI endpoints: register, login, OTP verify, refresh, logout, protected-route dependencies | Delegate identity to a third party (`AUTH-005`) |
| JWT/OTP Services | Backend-internal token issuance/validation and OTP generation/verification/email delivery | Live inside route handlers (must be decoupled) |

Full flow detail (state machine, lifetimes, rotation/reuse detection): [`docs/authentication.md`](./authentication.md).

## 4. Data Flow Across the Product Workflow

See [`docs/prd.md`](./prd.md) §4 for the user-facing workflow (`WF-001`). Architecturally, each step maps to a backend module boundary:

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

Because the client's own team will extend this codebase post-handoff using AI-assisted tools, module boundaries should be drawn along the table in §4 (one backend module per workflow step, each with its own router/service/schema files) rather than by technical layer alone. This keeps each module independently understandable — a future contributor (human or AI-assisted) working on, say, `report-generation` should not need to read `payment` internals to make a correct change.

Concretely, this means:
- Route handlers stay thin; business logic lives in per-module service functions (mirrors the JWT/OTP Services separation mandated for auth, generalized to every module).
- Database models are grouped by the entities in `docs/database-design.md`, not scattered.
- Cross-module coupling is limited to what §4 implies (e.g. `report-generation` reads `Facial Analysis Result` and `Questionnaire Response`, but does not reach into `authentication` internals beyond the standard "current user" dependency).

## 6. Non-Functional Considerations

| Concern | Note |
|---|---|
| Security | See [`docs/security.md`](./security.md) for the full posture (token/OTP handling, XSS trade-off, photo-validation-as-safety-gate). |
| Hosting | Explicitly undecided (`NFR-010`/`CON-007`). Architecture should not assume a specific platform's primitives (e.g. a specific queue/cron service) without flagging it as a swappable choice. |
| Third-party cost ownership | OpenAI/Stripe/Supabase/email provider usage costs are the client's responsibility (`BR-006`), not an architectural constraint but relevant to any usage-based design choice (e.g. how aggressively OpenAI is called). |
| Configurability | Report price (`OQ-002`) and photo-validation thresholds (`ASM-002`) must be configuration values, not hardcoded constants — both are explicitly undecided/deferred by the client. |

## 7. Open Questions / Assumptions Affecting Architecture

| ID | Item | Status |
|---|---|---|
| ASM-002 | Photo validation thresholds | Deferred to development time — architecture must make these configurable, not hardcode a guess now. |
| OQ-002 | Report price | Deferred — must be configurable. |
| NFR-010/CON-007 | Hosting platform | Undecided — do not couple architecture to a specific host's features. |
| — | Specific OTP email provider (SendGrid/SES/Postmark/etc.) | To be picked during development (`NFR-012`); architecture should isolate this behind an OTP-delivery interface so the choice is swappable. |

## 8. Related Documents

- [`docs/authentication.md`](./authentication.md) — full auth flow, token/OTP lifecycle.
- [`docs/security.md`](./security.md) — security posture and trade-offs.
- [`docs/database-design.md`](./database-design.md) — schema realizing the entities in §4.
- [`docs/api-specification.md`](./api-specification.md) — endpoint contracts realizing this architecture.
- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — how these modules are sequenced.
