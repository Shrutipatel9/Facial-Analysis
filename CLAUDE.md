# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Milestone 1 (client delivery Phase 1) is functionally complete** — auth, onboarding questionnaire, photo upload/validation, facial analysis engine, report generation, payment, and user dashboard are all implemented (see `docs/phase-wise-requirements.md` Phases 0–7, all marked Implemented).

**Milestone 2's first two phases are implementation-complete as of 2026-09-14 (not yet committed to git).** The client supplied two reference materials on 2026-09-11 (a competitor-product walkthrough video and its PDF report export) that scope out AI Visual Features (hairstyle/outfit/aging previews), an AI Beauty Assistant chat, and a richer interactive report — see `docs/milestone2_requirements.md` (requirements, `FR-018`/`FR-020`/`FR-022`), `docs/milestone2_phase_plan.md` (Implementation Phases 10–13), and **`docs/milestone2_home_and_report_spec.md`** (Home Overview + Report structure checklist).

- **Phase 10 ("report-enrichment")** — Facial Assessments + per-feature scores/harmony + per-feature AI before/after (`FR-018`/`FR-022`). TOC `/report` live. **Open presentation gap:** ship **Home Overview** as post-completion landing (video first screen) — do not keep Welcome-dashboard cards; see `milestone2_home_and_report_spec.md`.
- **Phase 11 ("AI Visual Features")** — hairstyle / outfit / aging (`FR-020`) live; generation may need retry after Gemini rate limits.

**Milestone 2 is complete as of 2026-09-17** (confirmed by the user) — Phases 10–13, including the AI Beauty Assistant chat and Settings/Billing restructure, are implemented. PayPal stays visible-disabled only (`BR-012`) — no working PayPal without client confirmation. The pre-Milestone-3 state is preserved untouched on the `demo/milestone2-stable` branch for client demo purposes; active development continues on `feature/milestone2-next` (or its successors) and merges to `main` only once a milestone's implementation is done.

**Milestone 3, five of six proposed phases implemented as of 2026-09-18 (not yet committed to git).** The delivery team proposed a feature set on 2026-09-17 by reviewing the live `qoves.com` reference site (the same reference business named in `BC-001`/`BC-002`). See `docs/milestone3_requirements.md` (`FR-023`–`FR-028`, all `[Recommendation]`) and `docs/milestone3_phase_plan.md` (Implementation Phases 14–19).

- **Implemented:** Phase 16 `protocol-enrichment` (`FR-025`, cost/cadence/difficulty per recommendation), Phase 14 `metrics-expansion` (`FR-023`, ~29 new landmark-derived metrics), Phase 15 `recommendation-visuals` (`FR-024`, descoped to metadata-only tagging — no new AI generation, per client decision), Phase 18 `support-channel` (`FR-027`, Settings → Contact Us, email relay), Phase 19 `marketing-landing` (`FR-028`, new Benefits section, no fabricated testimonials). Each has its own `D:\zzz\<module>\plans.md`.
- **Removed, not built:** Phase 17 `progress-tracking` (`FR-026`) — implemented 2026-09-17, then fully reverted 2026-09-18 at the client's explicit request ("I dont need the progress functionality remove it"). All code, its DB migration, and its module plan were deleted. See `docs/milestone3_phase_plan.md`'s Phase 17 section and `docs/milestone3_requirements.md`'s `FR-026` entry for the traceability record.

**Milestone 3.1 (production hardening, Phases 20–25) is complete as of 2026-09-22 (not yet committed to git).** Ahead of an actual production deployment, not a client-scope change — no `FR`/`AUTH`/`NFR`/`BR` item is added, changed, or removed. See `docs/milestone3.1_phase_plan.md` for the full per-phase detail; summary:

- **Implemented:** Phase 20 `ci-pipeline` (GitHub Actions for both apps, plus a first-ever lint/typecheck pass that surfaced and fixed real pre-existing debt), Phase 21 `background-job-durability` (a DB-backed crash-recovery reconciler for orphaned background AI tasks — no task queue introduced, see the phase doc's tradeoff writeup — and a real resumability bug fix in `report_visual_service.py`), Phase 22 `payment-cost-abuse-rate-limiting` (rate limits on the three paid-AI-call trigger endpoints, previously unlimited), Phase 23 `backend-observability-hardening` (a real DB-backed `/health` check, backend CSP, inert-until-configured Sentry wiring), Phase 24 `frontend-resilience-and-seo` (error/404 boundaries, `robots.ts`/`sitemap.ts` — none of these existed before), Phase 25 `deployment-artifacts` (Dockerfiles for both apps, `docker-compose.yml`, `docs/deployment.md` — both images built and one backend container smoke-tested for real, catching and fixing two real bugs in the process, see the phase doc).
- Error-tracking vendor (Sentry), manual-not-auto migrations on deploy, and single-instance-for-now were all explicit user decisions, not defaults picked silently — see the phase doc's "Decisions confirmed by the user" section.

**Milestone 4 (report intelligence upgrades + content hub, Phases 26–28) is complete as of 2026-09-22 (not yet committed to git).** Scoped the same way Milestone 3 was — reviewing qoves.com plus a broader AI beauty/skin-analysis competitor scan — then narrowed with the user via `AskUserQuestion` to two directions, explicitly excluding pricing/monetization and photo-quality-gating work and every still-deferred client-scope item. See `docs/milestone4_requirements.md` (`FR-029`–`FR-031`) and `docs/milestone4_phase_plan.md` (Implementation Phases 26–28).

- **Implemented:** Phase 26 `recommendation-tiering` (`FR-029`, AI-classified at-home/OTC/in-clinic tiering, zero new AI cost, keyword heuristic kept as a permanent fallback for pre-existing reports), Phase 27 `chat-compaction` (`FR-030`, bounds a long-lived chat conversation's context growth — replaces an originally-proposed "persistent chat memory" idea that turned out to already be fully built, see the requirements doc's own correction note), Phase 28 `insights-hub` (`FR-031`, a public `/insights` education section, 5 articles, content-only, explicitly no procedure/treatment or competitor-comparison content). One shared `D:\zzz\<module>\plans.md` per phase (three total).

This repo is a **from-scratch build**, two separate applications:

- **`Backend/`** — Python + FastAPI, `uv`-managed (`.python-version` pins ≥3.12). Auth module implemented (JWT/OTP, SQLAlchemy models, Alembic migrations, httpOnly refresh cookie). Real app entrypoint: `Backend/app/main.py`. `Backend/main.py` (repo-root stub) is an unrelated `uv`-generated artifact — ignore it.
- **`Frontend/`** (created as `frontend/`; Windows paths are case-insensitive so it's the same directory) — Next.js 16.3.4, React 19.2.8, TypeScript (`strict: true`), Tailwind CSS v4, ESLint 9. Auth module implemented (Zustand access-token store, AuthHydrator, API client with single-flight refresh, proactive refresh scheduler, auth route group + protected dashboard).

They communicate over HTTP/CORS — the Frontend calls the Backend's REST API directly from the browser. This is a confirmed architecture decision (resolves `client_requirements.md`'s `ASM-004`): **not** a single consolidated app, and the Backend is **not** being converted to Next.js/TypeScript.

## Source of truth

**`docs/client_requirements.md` is the single source of truth for this entire project.** Before implementing any feature, read the relevant section of that document. Key rules from it that apply to how you work here:

- Do not invent requirements not stated there. Anything not explicitly client-stated is labeled `[Recommendation]`, `[Assumption]`, or `[Decided by delivery team]` in that doc — preserve those labels if you carry requirements into code comments, PRs, or new docs.
- Derived documents under `docs/` (`architecture.md`, `authentication.md`, `api-specification.md`, `database-design.md`, `security.md`, `testing-strategy.md`, `phase-wise-requirements.md`, etc.) must stay consistent with `client_requirements.md`, not the other way around. Requirement IDs (`FR-*`, `AUTH-*`, `NFR-*`, `BR-*`, `WF-*`, `DATA-*`, `CON-*`) are the traceability mechanism between that doc and derived ones — reference them in code comments/PRs for non-obvious decisions.
- The client intends their own team to keep extending this codebase using AI-assisted tools post-handoff — this is the stated reason to favor clean, modular, conventional code over clever/opaque implementations (`BC-005`, `NFR-011`).
- This is an explicitly **phased** delivery. **As of v1.22, the client's scope has changed for part of Phase 2** — see "Project status" above and `docs/milestone2_requirements.md`/`docs/milestone2_phase_plan.md`. AI Visual Features and the AI Beauty Assistant chat are now Milestone 2 scope (not yet implemented); admin panel, report review workflow, email notifications, and Meta Pixel/GTM remain deferred with no scope change. PayPal's status is ambiguous (see `client_requirements.md` §2.2) — do not implement a working PayPal integration without explicit client confirmation. Do not build any still-deferred item unless the client's scope changes again — see `client_requirements.md` §2.2 and §12.
- Per-module implementation plans live under `D:\zzz\<module>\plans.md`, finalized at the point each module's implementation actually starts (not proactively ahead of time). Per-module `claude.md` files are created only when that module's implementation begins.

## Quality bar

The client has explicitly asked for a **premium, professional, highly interactive UI** — not a plain/default-styled or "college project" look — and **senior-level code quality** across the stack (clean architecture, proper typing on both sides, consistent conventions, no shortcuts). Treat this as a standing bar for every module's actual implementation, not just a one-off ask: real design effort on visual hierarchy, spacing, typography, micro-interactions, and empty/loading/error states, and idiomatic, well-structured code with no dead code or copy-paste duplication. This is in addition to, not a replacement for, `NFR-011`/`BC-005` above.

Two standing UI conventions established in the auth module, applying to **every** future module (`BR-009`, `BR-010`; full detail in `docs/ui-ux-design.md` §4):
- Every user-initiated action with a real success/failure outcome shows exactly one toast (top-right, via `sonner`) — never silent.
- Every destructive/irreversible action (delete, logout, revoke, etc.) is confirmed via the shared `ConfirmDialog` (`frontend/src/components/ui/confirm-dialog.tsx`) before it executes — never fired directly on click.

## Architecture (target, per client_requirements.md v1.5)

**Stack:** Next.js 16.3.4 (App Router, TypeScript) frontend + Python/FastAPI backend (SQLAlchemy + Alembic) — two separate applications over HTTP/CORS · vendor-neutral PostgreSQL (no longer Supabase — `NFR-002`) · Zustand for frontend state (superseded from Redux, `NFR-006`) · Tailwind CSS v4 for styling · MediaPipe/OpenCV (in-process in the Python backend) for facial measurement · OpenAI for narrative generation · Stripe for payment.

**Authentication is custom and backend-owned — this is a hard constraint, not a default choice.** No third-party auth-as-a-service (Supabase Auth, Auth0, Firebase Auth, etc.) may ever be used as the auth mechanism (`AUTH-001`, `CON-002`). The required layering (must be preserved in any implementation, now spanning two apps):

```
UI → Zustand Auth Store → API Client → Backend Auth APIs → JWT/OTP Services
   |______ Frontend (Next.js) ______|  |___ Backend (FastAPI) ___|
```

- UI components never touch raw tokens; auth flows go through the API client / store (`FE-007`).
- **Token storage (v1.4 / `FE-002`):** access token + user live in the in-memory Zustand store; refresh token is an **httpOnly cookie** only. Never `localStorage` / `sessionStorage`, and never Zustand `persist` middleware for auth.
- The frontend reaches the API via a **same-origin Next.js rewrite** (`/api/backend/*` → FastAPI) so the refresh cookie is first-party on the frontend origin. Do not point `NEXT_PUBLIC_API_URL` at `http://localhost:8000` in the browser — cross-origin cookies break restore-on-reload.
- Session persistence: on startup, module-level `bootstrapSession()` (single-flight, Strict-Mode safe) calls `POST /auth/refresh` while `status === "idle"`. Protected routes **wait** during that window.
- A centralized session module attaches the access token, sends cookies with `credentials: "include"`, performs **proactive** refresh ~1 minute before access-token expiry, and handles **401 → refresh → retry** with a single-flight guard. Parallel `/auth/refresh` calls are forbidden (they race rotation and can revoke the session).
- Access-token expiry, page refresh, tab/window/browser close, network errors, and 5xx must **not** clear auth or redirect. Only **explicit logout** or a **backend-confirmed invalid refresh session** (401 from `/auth/refresh`) may.
- Backend auth flow: both signup and login are two-step — email+password first, then mandatory OTP verification (email-delivered) — only after OTP success are the access token (JSON) and refresh cookie issued. Refresh-token rotation with reuse detection remains the highest-risk auth piece (`WF-002`).
- OTP/token parameters: OTP 10-min expiry / 60s resend cooldown / 5 attempts before 15-min lockout, hashed at rest; access token 15 min; refresh token **7 days**, rotated per use (`AUTH-010`–`AUTH-012`). Cookie CSRF: `X-Requested-With` + Origin allow-list on refresh/logout. Frontend and API send security headers (CSP/HSTS in production). See `docs/security.md` §4–8 for the production deploy checklist.

**Core domain pipeline (Phase 1):** landing → signup/login (see above) → 23-question branching onboarding questionnaire ending in a mandatory BDD/informational-only disclaimer checkbox (submission blocked without it) → multi-angle photo upload with backend-enforced validation (not just a UI checklist — exact thresholds are intentionally undecided, to be set during implementation) → MediaPipe/OpenCV landmark extraction → OpenAI narrative generation using *both* the CV measurements and the questionnaire answers as context → an 11-feature report (Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears — this exact set is fixed, `FR-009`/`BR-008`) → auto-publish (no admin review gate exists in Phase 1) → Stripe payment gates full report access (a teaser may be shown pre-payment) → user dashboard (report history, PDF download, payment history, profile).

Data entities to expect when building the schema: User, OTP Record, Refresh Token/Session Record, Questionnaire Response, Photo, Facial Analysis Result, Report, Payment — see `DATA-*` in the requirements doc for fields/relationships.

## Development commands

### `Backend/` — FastAPI (Python)
Uses `uv` for dependency management.
```
cd Backend
uv sync                                # install dependencies
uv run uvicorn app.main:app --reload   # run the dev server (localhost:8000)
uv run pytest                          # run tests
uv run alembic upgrade head            # apply migrations
```

### `Frontend/` — Next.js (TypeScript)
```
cd Frontend
npm install
npm run dev       # start dev server (Turbopack) at localhost:3000
npm run build     # production build
npm run start     # run a production build
npm run lint      # eslint (eslint-config-next)
```
