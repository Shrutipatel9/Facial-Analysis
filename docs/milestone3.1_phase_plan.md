# Milestone 3.1 — Phase Plan (Production Hardening)

**Source of truth:** This document sequences pure production-hardening work identified via direct code investigation of `Backend/` and `frontend/` on 2026-09-22, ahead of an actual production deployment. Unlike [`milestone3_phase_plan.md`](./milestone3_phase_plan.md) (Implementation Phases 14–19, new `FR-023`–`FR-028` functional requirements), **no `client_requirements.md` `FR`/`AUTH`/`NFR`/`BR` item is added, changed, or removed by this milestone** — every phase below is infrastructure/reliability/security posture only, so there is no companion `milestone3.1_requirements.md`. Continues Milestone 3's Implementation Phase numbering (14–19) at **20**.

**Status:** Phases 20–24 implementation-complete as of 2026-09-22 (not yet committed to git). Phase 25 in progress.

**Version:** 1.0 (2026-09-22).

---

## Phase Overview & Module Map

| Implementation Phase | Name | Module | `plans.md` location |
|---|---|---|---|
| 20 | CI Pipeline | `ci-pipeline` | `D:\zzz\production-hardening\plans.md` |
| 21 | Background-Job Durability | `background-job-durability` | `D:\zzz\production-hardening\plans.md` |
| 22 | Rate-Limit Paid Endpoints | `payment-cost-abuse-rate-limiting` | `D:\zzz\production-hardening\plans.md` |
| 23 | Logging / Error-Tracking / Real Health Check | `backend-observability-hardening` | `D:\zzz\production-hardening\plans.md` |
| 24 | Frontend Error Boundaries + Basic SEO | `frontend-resilience-and-seo` | `D:\zzz\production-hardening\plans.md` |
| 25 | Deployment Artifacts | `deployment-artifacts` | `D:\zzz\production-hardening\plans.md` |

All six phases share one module plan file (`D:\zzz\production-hardening\plans.md`) rather than one each — this milestone is one coherent hardening pass by the same contributor in one session, not six independently-scheduled modules the way Milestone 3's phases were.

**Dependency chain:**

```
20 (CI)  ── safety net, do first ───────────────────────┐
21 (Background-job durability)  ─┐  independent of        │
22 (Rate-limit paid endpoints)   │  each other, any order   │
23 (Logging/health/CSP/docs)     │                          │
24 (Frontend error boundaries+SEO)┘                         │
25 (Deployment artifacts) ── packages 20-24, do last ◄──────┘
```

**AI-cost posture (every phase):** verifiable through the existing fully-mocked `pytest` suite (`tests/conftest.py`'s `ai_recorder`/`email_sender` fixtures, `OPENAI_API_KEY=""` forced in tests) plus `tsc`/`eslint`/`ruff`/`mypy`. No phase requires a real paid OpenAI/Stripe/Gemini call to verify.

---

## Phase 20 — CI Pipeline

**Objective:** Wire the existing, already-mocked test suite into CI so nothing merges without it passing.

**Scope:** `.github/workflows/backend.yml` (Postgres service container, `uv sync`, `ruff check`, `mypy app`, `alembic upgrade head` against an empty DB, `pytest`) and `.github/workflows/frontend.yml` (`npm ci`, `eslint`, `tsc --noEmit`, `npm run build`).

**Prerequisite work discovered mid-phase:** the repo had never actually been linted/typechecked as a gate before — bringing `ruff`/`mypy` into CI surfaced 80 pre-existing `ruff` violations and 2 `mypy` errors (all fixed, see commit) plus 2 pre-existing `react-hooks/set-state-in-effect` ESLint errors on the frontend (fixed via deferring the setState calls past the effect's synchronous execution). One ruff auto-fix regression was caught and reverted: its import-block-merge fix silently dropped a renamed re-export (`IDENTITY_MISMATCH_THRESHOLD` in `photo_validation_service.py`) — fixed manually, `pyproject.toml`'s `alembic/versions/*.py` now has a documented `E501` per-file-ignore (generated migration files are never hand-edited for line length once they've run against a real database).

**Acceptance criteria:** Met — `ruff`/`mypy` both clean, full backend suite green (487 → 514 across all six phases), frontend `tsc`/`eslint`/`build` clean.

**AI-touch:** None.

## Phase 21 — Background-Job Durability

**Objective:** Fix "a process restart mid-task loses the task silently, forever" (`app/core/background_tasks.py` — bare `asyncio.create_task()`, no queue anywhere in this stack).

**Design decision — DB-backed reconciler, not a task queue.** A single-instance app with a durability problem, not a throughput problem; `AiVisual`/`ReportFeatureVisual` already had `status`/`updated_at` columns and a partial self-healing pattern (`ai_visual_service.get_or_create_visuals`) this phase generalizes into an automatic sweep, rather than introducing new infrastructure (Redis, a worker process, a new deployment topology). Revisit only if multi-instance horizontal scaling is ever actually needed.

**Scope (implemented):**
- `FacialAnalysisResult.updated_at` added (migration `cc5f9ab0e1e0`).
- `app/services/reconciler_service.py` (new): `reconcile_analyses`/`reconcile_ai_visuals`/`reconcile_report_visuals`/`run_reconciler_sweep`, each finding rows stuck past `RECONCILER_STUCK_THRESHOLD_MINUTES` (default 20) and resuming or resetting them, capped at `RECONCILER_MAX_RESUMED_PER_SWEEP` (default 5) per sweep.
- `analysis_service.py` refactored: `run_analysis_pipeline`'s narrative+completion tail extracted into `_run_narrative_and_complete`/`_finalize_completed`, shared with the new `resume_analysis_pipeline` (three branches: CV not done → re-run whole pipeline; CV done, narrative not done → resume narrative only; both done → just finalize — never re-pays for an already-succeeded step).
- `ai_visual_service.reset_stuck_generating` (new) — resets only the crash-orphaned "generating" row(s) for a kind.
- **Real bug found and fixed in `report_visual_service.generate_all_feature_visuals`:** it iterated all 11 `ANALYSIS_FEATURES` unconditionally with no guard against an already-`"generated"` feature — harmless before anything could call it a second time, but the reconciler is exactly that second caller. Now filters to `pending_features` (status != "generated") before scheduling, with a matching defensive per-row check inside `_generate_one_feature_visual`, mirroring `ai_visual_service`'s existing pattern. `report_visual_service.reset_stuck_rows` (new) added alongside it.
- `app/main.py`: FastAPI `lifespan` runs one sweep at startup, then a periodic loop (`RECONCILER_SWEEP_INTERVAL_SECONDS`, default 300s).
- Claim-before-dispatch: `reconcile_analyses` touches `updated_at` on selected rows before scheduling their resume (a real narrative call can itself take several minutes, so without this the *next* sweep would re-select and duplicate-resume the same still-in-flight analysis).

**Testing:** `tests/integration/test_reconciler_service.py` (11 tests) — stuck-vs-fresh row detection for all three tables, all three `resume_analysis_pipeline` branches, and a direct regression test proving an already-generated report feature is never regenerated on resume. Zero real AI calls (`ai_recorder` + a local `FakeImageClient`).

**Deviation from the original plan:** did not also add staleness-awareness to `ai_visual_service.get_or_create_visuals`'s own lazy check (the plan's item 4) — the periodic reconciler sweep already covers this case without a page revisit, so a second, duplicated staleness check there would be redundant complexity for no added coverage.

**AI-touch:** None in the fix itself (fully covered by the mocked pattern) — a resumed task making a real call in production afterward is the intended behavior working correctly, not a new testing obligation.

## Phase 22 — Rate-Limit Paid Endpoints

**Objective:** Close a direct, unbounded cost-abuse surface — `slowapi` was wired app-level but only actually applied to `auth.py`/`support.py`; `POST /payments/checkout`, `POST /analysis`, `POST /ai-visuals/{kind}` had zero rate limiting.

**Scope (implemented):** `@limiter.limit("5/hour")` on `create_checkout` and `trigger_analysis`; `@limiter.limit("10/hour")` on `create_visuals`. `GET /analysis/status`/`GET /analysis/{id}` and `ai-visuals`' list/image reads deliberately left unlimited (polled frequently and legitimately during generation — rate-limiting them would break normal UX, not stop cost abuse). Stripe's webhook deliberately excluded (already protected by signature verification; IP-throttling a webhook whose caller IPs are Stripe's own rotating ranges risks dropping legitimate retries).

**Real finding during implementation:** slowapi's default key scoping is **per exact request path**, not per route-function — confirmed empirically via `tests/integration/test_rate_limiting.py`. This means each `{kind}` value on `POST /ai-visuals/{kind}` (hairstyle/outfit/aging/potential) gets its own **independent** 10/hour bucket, not one shared bucket across all four as originally assumed — the endpoint's own docstring and this doc are corrected to reflect that.

**Testing:** `tests/integration/test_rate_limiting.py` (4 tests) — Nth+1 request returns 429/`RATE_LIMITED` for all three endpoints, plus a test proving the ai-visuals bucket is genuinely independent per kind. Zero real AI/Stripe calls (rejection happens in middleware before the service layer is ever reached).

**AI-touch:** None.

## Phase 23 — Logging / Error-Tracking / Real Health Check

**Objective:** Round out backend observability basics.

**Scope (implemented):**
- `GET /health` now runs a real `SELECT 1` against Postgres, returns `{"status": "ok", "checks": {"database": "ok"}}` / 200 on success, `{"status": "degraded", ...}` / 503 on failure — replaces the previous static `{"status": "ok"}`.
- `SecurityHeadersMiddleware` now sets `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` on every backend response except `/docs`/`/redoc`/`/openapi.json` (dev-only, need Swagger's inline scripts) — the backend is a pure JSON API in production, so this is much stricter than the frontend's own necessarily looser CSP (`next.config.ts`, still `'unsafe-inline'`/`'unsafe-eval'` for Next.js compatibility — that remains a separate, not-yet-done follow-up, deliberately out of scope for this milestone).
- Docs-gating (`app/main.py`'s `docs_url`/`redoc_url`/`openapi_url`) was **already correct** — this phase added only a regression test, no new gating code.
- `app/core/error_tracking.py` (new) — Sentry, inert unless `SENTRY_DSN` is set (`sentry-sdk[fastapi]` added as a dependency). `before_send` reuses `app/core/logging.py`'s `redact()` on the event's message/exception/breadcrumb text, and `send_default_pii=False` keeps request bodies/headers/cookies out of events at the SDK-config level.

**Testing:** `tests/integration/test_production_hardening.py` (`/health` 200/503, CSP presence, docs-gating regression) + `tests/unit/test_error_tracking.py` (inert-without-DSN, initializes-with-DSN, redaction). Zero real AI calls; Sentry SDK `init` itself is monkeypatched in tests, never actually contacting Sentry.

**Still open (per the plan, correctly not decided here):** the user has confirmed Sentry as the vendor and manual (not auto-run) Alembic migrations on deploy — both already reflected above/in `docs/deployment.md`. Provisioning the actual Sentry account/DSN remains the user's own action.

**AI-touch:** None.

## Phase 24 — Frontend Error Boundaries + Basic SEO

**Objective:** Close "zero error boundaries anywhere in `frontend/src/app/`" and "no SEO basics."

**Scope (implemented):** `app/not-found.tsx` (server component, styled 404, matches the app's premium-UI bar), `app/error.tsx` (client component, catches a render error anywhere under the root layout, "Try again"/"Back to home" actions, never renders `error.message`/stack to the user — only `error.digest` and a console log), `app/global-error.tsx` (catches an error in the root layout itself; necessarily self-contained/dependency-free since it replaces the whole layout when triggered), `app/robots.ts` + `app/sitemap.ts` (typed App Router conventions; only `/` is real public content — `(auth)`/`(protected)` routes are disallowed or naturally unindexable), `NEXT_PUBLIC_SITE_URL` env var (new, defaults to `localhost:3000`) backing both plus `metadataBase`/`openGraph`/a title template in the root layout.

**Verification:** `tsc --noEmit` + `eslint` + `npm run build` all clean; visually confirmed in the browser against the user's already-running dev server (`/this-page-does-not-exist` → styled 404 with correct `<title>Page not found | FaceIQ</title>`; `/robots.txt` renders correctly) — no new dev server started, no disruption to the user's session.

**Deviation from the original plan:** root-level error boundaries only, no `(protected)/error.tsx` scoped fallback — matches the plan's own stated default (add a scoped one later only if a real need shows up). No test framework added (confirmed none existed before; this repo's convention stays `tsc`+`eslint` only).

**AI-touch:** None.

## Phase 25 — Deployment Artifacts

**Objective:** A platform-agnostic, Docker-based way to build and run both apps in a production-like topology, no cloud/PaaS vendor commitment.

**Scope (implemented):** `Backend/Dockerfile` (multi-stage, `uv`-based, single Uvicorn process — see the durability note above for why not multi-worker), `frontend/Dockerfile` (standard Next.js `output: "standalone"` multi-stage build, added to `next.config.ts`), `.dockerignore` for both apps, root `docker-compose.yml` (Postgres + backend + frontend, Postgres port **not** published to the host — matches `docs/security.md` §8's "Postgres not publicly reachable" item, contrast with `Backend/docker-compose.yml`'s dev-only version which does publish it), `docs/deployment.md` (new — build/run instructions, required env vars, manual-migration step, health-check/reconciler recovery story, backup mechanism).

**Real finding during implementation:** `next.config.ts`'s `BACKEND_URL` read is evaluated at Next.js server *start* (both `next build` and `next start`/the standalone `server.js` re-load the config module fresh), not baked into the image at build time — confirmed against Next.js's documented `next.config.js` env-var loading behavior. `docker-compose.yml` therefore sets `BACKEND_URL` as a **runtime** environment variable on the `frontend` service, not a Docker build arg (an earlier draft incorrectly included both; the unused build arg was removed).

**Verification:** `docker build` run for both images (see session log); `docker compose up`-style end-to-end verification is the user's own to run once real `.env.docker` values exist, per this milestone's "don't spend real tokens on testing" posture — a real deploy exercises `OPENAI_API_KEY`/`STRIPE_SECRET_KEY` credentials this session never touches.

**AI-touch:** None — building/running containers and hitting `/health` involve zero AI/Stripe calls.

---

## Decisions confirmed by the user (before implementation began)

1. **Error tracking: Sentry**, inert until a DSN is provisioned.
2. **Migrations on deploy: manual step**, not auto-run on container start.
3. **Single-instance for now** — the reconciler is not multi-worker-safe, `Backend/Dockerfile` runs one Uvicorn process. Revisit both together if horizontal scaling is ever actually needed.

## Related documents

- [`docs/deployment.md`](./deployment.md) — the actual build/run instructions Phase 25 produced
- [`docs/security.md`](./security.md) — the production deploy checklist this milestone's Phase 23/25 work feeds into
- [`docs/milestone3_phase_plan.md`](./milestone3_phase_plan.md) — Implementation Phase numbering convention this document continues
