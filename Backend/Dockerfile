# Milestone 3.1, Phase 25 (production hardening) -- platform-agnostic,
# Docker-based build. Deployment target is deliberately undecided (see
# docs/deployment.md), so this targets no specific cloud/PaaS vendor.
#
# Single-stage Uvicorn process by design: app/services/reconciler_service.py
# (Phase 21's crash-recovery sweep) is not built multi-worker-safe -- see
# its module docstring. Do not add --workers or run multiple replicas of
# this image without first making the reconciler leader-elect/lock itself.

FROM python:3.12-slim AS builder

# uv installed via the official static binary, not pip -- avoids needing a
# build toolchain in this stage just to install the installer itself.
# Pinned to match this repo's own local uv version.
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependencies resolved from the lockfile before app code is copied in, so
# an app-code-only change doesn't invalidate this (slow: mediapipe/opencv/
# reportlab are large wheels) layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY . .
RUN uv sync --locked --no-dev


FROM python:3.12-slim AS runtime

# mediapipe/opencv-python-headless both dynamically link against libGL at
# import time even in "headless" mode -- absent on a bare python:3.12-slim
# base, and the resulting ImportError is not an obvious one to debug on a
# first deploy.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else 1)"

# Alembic migrations are a deliberate manual deploy step, not run here --
# see docs/deployment.md (auto-migration-on-start risks two replicas
# racing a migration; a manual step is safer even though it's one more
# thing to remember).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
