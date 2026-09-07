# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repo is a **from-scratch, pre-implementation** build. Both `Backend/` and `Frontend/` currently contain only scaffolding (default FastAPI hello-world app, default `create-vite` React template) — no product features are implemented yet. Do not assume any existing code reflects intended architecture; treat it as a starting point to build on or replace.

## Source of truth

**`docs/client_requirements.md` is the single source of truth for this entire project.** Before implementing any feature, read the relevant section of that document. Key rules from it that apply to how you work here:

- Do not invent requirements not stated there. Anything not explicitly client-stated is labeled `[Recommendation]`, `[Assumption]`, or `[Decided by delivery team]` in that doc — preserve those labels if you carry requirements into code comments, PRs, or new docs.
- If derived documents (`PRD.md`, `ARCHITECTURE.md`, `API_SPECIFICATION.md`, `DATABASE_DESIGN.md`, `AUTHENTICATION.md`, `SECURITY.md`, etc.) are created later, they must stay consistent with `client_requirements.md`, not the other way around. Requirement IDs (`FR-*`, `AUTH-*`, `NFR-*`, `BR-*`, `WF-*`, `DATA-*`, `CON-*`) are the traceability mechanism between that doc and derived ones — reference them in code comments/PRs for non-obvious decisions.
- The client intends their own team to keep extending this codebase using AI-assisted tools post-handoff — this is the stated reason to favor clean, modular, conventional code over clever/opaque implementations (`BC-005`, `NFR-011`).
- This is an explicitly **phased** delivery. Do not build Phase 2 features (admin panel, report review workflow, email notifications, PayPal, Meta Pixel/GTM, AI visual features (hairstyle/outfit/aging), AI Beauty Assistant chat, formal data-retention policy) unless the client's scope changes — see `client_requirements.md` §2.2 and §12.

## Architecture (target, per client_requirements.md)

**Stack:** Python/FastAPI backend (SQLAlchemy + Alembic, Supabase Postgres for data only) · React + Vite frontend (Redux Toolkit) · MediaPipe/OpenCV for facial measurement · OpenAI for narrative generation · Stripe for payment.

**Authentication is custom and backend-owned — this is a hard constraint, not a default choice.** Supabase is Postgres hosting only; it must never be used as the auth mechanism. The required layering (must be preserved in any implementation):

```
UI → Redux Auth Store → API Client → Backend Auth APIs → JWT/OTP Services
```

- UI components never call auth APIs or touch tokens directly.
- Redux holds both the access token and refresh token (explicitly not `localStorage` — client-confirmed decision, see `FE-002`/`ASM-001`).
- A centralized API client attaches the access token to requests and handles refresh-on-401 transparently.
- Backend auth flow: both signup and login are two-step — email+password first, then mandatory OTP verification (email-delivered) — only after OTP success are JWT access+refresh tokens issued. See `WF-002` in the requirements doc for the full state machine, including refresh-token rotation with reuse detection (a reused/rotated-out refresh token revokes the whole token family).
- OTP/token parameters are fixed: OTP 10-min expiry / 60s resend cooldown / 5 attempts before 15-min lockout, hashed at rest; access token 15 min; refresh token 30 days, rotated per use. Don't rederive these — they're settled (`AUTH-010`–`AUTH-012`).

**Core domain pipeline (Phase 1):** landing → signup/login (see above) → 23-question branching onboarding questionnaire ending in a mandatory BDD/informational-only disclaimer checkbox (submission blocked without it) → multi-angle photo upload with backend-enforced validation (not just a UI checklist — exact thresholds are intentionally undecided, to be set during implementation) → MediaPipe/OpenCV landmark extraction → OpenAI narrative generation using *both* the CV measurements and the questionnaire answers as context → an 11-feature report (Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears — this exact set is fixed, `FR-009`/`BR-008`) → auto-publish (no admin review gate exists in Phase 1) → Stripe payment gates full report access (a teaser may be shown pre-payment) → user dashboard (report history, PDF download, payment history, profile).

Data entities to expect when building the schema: User, OTP Record, Refresh Token/Session Record, Questionnaire Response, Photo, Facial Analysis Result, Report, Payment — see `DATA-*` in the requirements doc for fields/relationships.

## Development commands

### Backend (`Backend/`)
Uses `uv` for dependency management (`uv.lock` present, Python >=3.12 pinned via `.python-version`).
```
cd Backend
uv sync                 # install dependencies
uv run uvicorn app.main:app --reload   # run the FastAPI dev server
```
The FastAPI app lives in `Backend/app/main.py` (currently just a `/health` endpoint). `Backend/main.py` is an unrelated `uv`-generated entry-point stub, not the app.

### Frontend (`Frontend/`)
Standard Vite/npm project.
```
cd Frontend
npm install
npm run dev       # start dev server with HMR
npm run build     # production build
npm run lint      # eslint
npm run preview   # preview a production build locally
```

No test suites, CI config, or linting for the backend exist yet — set these up following the stack choices above (FastAPI/SQLAlchemy conventions) if asked to add them, rather than introducing a different stack.
