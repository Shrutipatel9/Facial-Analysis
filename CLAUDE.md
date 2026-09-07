# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repo is a **from-scratch build**, two separate applications:

- **`Backend/`** — Python + FastAPI, `uv`-managed (`.python-version` pins ≥3.12). Auth module implemented (JWT/OTP, SQLAlchemy models, Alembic migrations, httpOnly refresh cookie). Real app entrypoint: `Backend/app/main.py`. `Backend/main.py` (repo-root stub) is an unrelated `uv`-generated artifact — ignore it.
- **`Frontend/`** (created as `frontend/`; Windows paths are case-insensitive so it's the same directory) — Next.js 16.3.4, React 19.2.8, TypeScript (`strict: true`), Tailwind CSS v4, ESLint 9. Auth module implemented (Zustand access-token store, AuthHydrator, API client with single-flight refresh, proactive refresh scheduler, auth route group + protected dashboard).

They communicate over HTTP/CORS — the Frontend calls the Backend's REST API directly from the browser. This is a confirmed architecture decision (resolves `client_requirements.md`'s `ASM-004`): **not** a single consolidated app, and the Backend is **not** being converted to Next.js/TypeScript.

## Source of truth

**`docs/client_requirements.md` is the single source of truth for this entire project.** Before implementing any feature, read the relevant section of that document. Key rules from it that apply to how you work here:

- Do not invent requirements not stated there. Anything not explicitly client-stated is labeled `[Recommendation]`, `[Assumption]`, or `[Decided by delivery team]` in that doc — preserve those labels if you carry requirements into code comments, PRs, or new docs.
- Derived documents under `docs/` (`architecture.md`, `authentication.md`, `api-specification.md`, `database-design.md`, `security.md`, `testing-strategy.md`, `phase-wise-requirements.md`, etc.) must stay consistent with `client_requirements.md`, not the other way around. Requirement IDs (`FR-*`, `AUTH-*`, `NFR-*`, `BR-*`, `WF-*`, `DATA-*`, `CON-*`) are the traceability mechanism between that doc and derived ones — reference them in code comments/PRs for non-obvious decisions.
- The client intends their own team to keep extending this codebase using AI-assisted tools post-handoff — this is the stated reason to favor clean, modular, conventional code over clever/opaque implementations (`BC-005`, `NFR-011`).
- This is an explicitly **phased** delivery. Do not build Phase 2 features (admin panel, report review workflow, email notifications, PayPal, Meta Pixel/GTM, AI visual features (hairstyle/outfit/aging), AI Beauty Assistant chat, formal data-retention policy) unless the client's scope changes — see `client_requirements.md` §2.2 and §12.
- Per-module implementation plans live under `D:\zzz\<module>\plans.md`, finalized at the point each module's implementation actually starts (not proactively ahead of time). Per-module `claude.md` files are created only when that module's implementation begins.

## Quality bar

The client has explicitly asked for a **premium, professional, highly interactive UI** — not a plain/default-styled or "college project" look — and **senior-level code quality** across the stack (clean architecture, proper typing on both sides, consistent conventions, no shortcuts). Treat this as a standing bar for every module's actual implementation, not just a one-off ask: real design effort on visual hierarchy, spacing, typography, micro-interactions, and empty/loading/error states, and idiomatic, well-structured code with no dead code or copy-paste duplication. This is in addition to, not a replacement for, `NFR-011`/`BC-005` above.

## Architecture (target, per client_requirements.md v1.4)

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
