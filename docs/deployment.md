# Deployment (Milestone 3.1, Phase 25)

**Source of truth:** this document covers *how* to build and run the two apps in a production-like topology. It does not restate the security checklist — see [`docs/security.md` §8](./security.md#8-production-deploy-checklist) for that, and complete it before any real deploy.

**Hosting target is deliberately undecided** (`client_requirements.md` `NFR-010`/`CON-007`). Everything below is platform-agnostic (plain Docker/Docker Compose), not tied to a specific cloud provider or PaaS. Pick a host, then adapt these images/compose file to that platform's own deploy mechanism (its own container runtime almost certainly already understands a Dockerfile directly).

## 1. Topology

```
browser → Next.js (HTTPS, port 3000) → rewrite /api/backend/* → FastAPI (port 8000) → Postgres
```

Same topology `docs/security.md` §8 already assumes for the cookie model (`SameSite=Strict` requires the refresh cookie to be first-party on the frontend origin) — see that doc before changing it.

## 2. Images

- `Backend/Dockerfile` — multi-stage, `uv`-based, runs `uvicorn app.main:app` as a **single process**. Do not add `--workers` or run multiple replicas of this image without first making `app/services/reconciler_service.py`'s crash-recovery sweep multi-worker-safe (it's not today — no leader-election/locking, see its module docstring and Milestone 3.1's Phase 21 design notes).
- `frontend/Dockerfile` — standard Next.js multi-stage build using `output: "standalone"` (`next.config.ts`) for a slim final image.

Both images run as a non-root user and expose a `HEALTHCHECK` hitting the same endpoints described below.

## 3. Required environment variables

Set via `Backend/.env.docker` and `frontend/.env.docker` (not committed — see the `.gitignore`/`.dockerignore` entries; base them on `Backend/.env.example` and `frontend/.env.local.example`). The full list of what each var does is documented inline in those `.example` files — this section only calls out deploy-specific ones:

- `Backend/.env.docker`: everything in `.env.example`, plus a real `DATABASE_URL`, `JWT_SECRET`/`OTP_PEPPER` (never placeholders — `docs/security.md` §8), `CORS_ORIGINS` set to the real frontend origin, `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET`, `EMAIL_PROVIDER=smtp` with real SMTP credentials, and optionally `SENTRY_DSN` (Milestone 3.1 Phase 23 — inert until set).
- `frontend/.env.docker`: `NEXT_PUBLIC_API_URL=/api/backend` (same-origin proxy — never point the browser at the API origin directly, breaks the refresh cookie), `BACKEND_URL` = the backend's internal address (read fresh at container start by `next.config.ts`, not baked into the image at build time — a plain runtime env var, not a Docker build arg).

`docker-compose.yml` (root of the repo) overrides `DATABASE_URL`/`BACKEND_URL` to the compose network's own service hostnames (`db`/`backend`) regardless of what's in the `.env.docker` files, since those hostnames only resolve inside that specific compose network.

## 4. Running locally (verification, not a deploy target)

```
cp Backend/.env.example Backend/.env.docker        # fill in real values
cp frontend/.env.local.example frontend/.env.docker # fill in real values
docker compose up --build
```

Brings up Postgres (not published to the host — `docs/security.md` §8's "Postgres not publicly reachable" item, unlike `Backend/docker-compose.yml`'s dev-only version which does publish it on `5433`), the backend on `:8000`, and the frontend on `:3000`. This is for confirming the images/topology actually work before choosing a real host, not itself a deployment mechanism.

## 5. Database migrations

**Manual step, deliberately not run automatically on container start.** After deploying a new backend image:

```
docker compose exec backend uv run alembic upgrade head
```

(or the equivalent one-off command on whatever host is chosen). This was a real tradeoff, not a default picked silently: auto-running migrations in the container entrypoint is more convenient, but risks two replicas racing the same migration if this ever scales beyond one instance, and a botched auto-migration is a worse failure mode than a manual step that's easy to skip once and notice. Revisit only together with the single-instance constraint in §2 above.

## 6. Health checks

`GET /health` (backend) does a real `SELECT 1` against Postgres and returns 503 if the database is unreachable (Milestone 3.1 Phase 23) — this is what both the Docker `HEALTHCHECK` directives and any external load balancer/orchestrator health check should point at. The frontend's `HEALTHCHECK` just confirms the Next.js server itself is responding.

## 7. Crash recovery

`app/services/reconciler_service.py` (Milestone 3.1 Phase 21) runs one sweep at backend startup and then periodically (`RECONCILER_SWEEP_INTERVAL_SECONDS`, default 300s) — this is the intended recovery story for a background AI generation task (narrative/image-gen) that was mid-flight when a container restarts. No separate recovery step is needed after a redeploy; the sweep runs automatically on the new container's own startup.

## 8. Backups

Mechanism only — schedule/retention/storage specifics depend on the still-undecided host, and belong in a follow-up once that's chosen:

```
docker compose exec db pg_dump -U facial_analysis facial_analysis > backup-$(date +%Y%m%d).sql
```

Run this on a schedule (cron, or whatever the chosen host's own scheduled-job mechanism is) and store the output somewhere other than the same disk as the database itself.

## 9. Related documents

- [`docs/security.md`](./security.md) — the actual production checklist; complete it before deploying
- [`docs/milestone3.1_phase_plan.md`](./milestone3.1_phase_plan.md) — Phase 25's full scope, including the durability/rate-limiting/observability work this deploy setup builds on
