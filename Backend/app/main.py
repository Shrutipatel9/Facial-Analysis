import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.error_tracking import init_error_tracking
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import async_session_factory
from app.exception_handlers import register_exception_handlers
from app.services.reconciler_service import run_reconciler_sweep

logger = logging.getLogger(__name__)


async def _reconciler_loop(interval_seconds: int) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await run_reconciler_sweep()
        except Exception:  # noqa: BLE001 -- a sweep failure must never kill the loop, just retry next interval
            logger.exception("Reconciler sweep failed")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001 -- app required by FastAPI's lifespan signature
    settings = get_settings()
    # Milestone 3.1, Phase 21: one sweep at startup (catches whatever the
    # previous process left orphaned), then a periodic sweep for anything
    # that gets orphaned while this process is running. See
    # app/services/reconciler_service.py's module docstring for why this is
    # a DB-backed sweep, not a task queue.
    #
    # Caught, not left to propagate: a real deploy scenario surfaced this
    # directly -- starting a new backend image before its migration has
    # been applied (docs/deployment.md's manual-migration step) makes this
    # very first sweep fail with a schema-mismatch DB error, which would
    # otherwise crash the entire app at startup over what is a best-effort
    # resilience feature, not a critical path. The periodic loop already
    # tolerates a failed sweep the same way (see _reconciler_loop above);
    # startup should too, for the same reason.
    try:
        await run_reconciler_sweep()
    except Exception:  # noqa: BLE001 -- see comment above: must never block app startup
        logger.exception("Startup reconciler sweep failed")
    loop_task = asyncio.create_task(_reconciler_loop(settings.reconciler_sweep_interval_seconds))
    yield
    loop_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await loop_task


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(logging.DEBUG if settings.is_development else logging.INFO)
    init_error_tracking()

    app = FastAPI(
        title="Facial Analysis API",
        version="1.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=_lifespan,
    )

    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please slow down and try again shortly.",
                }
            },
        )

    # Last added = outermost. Order: TrustedHost → SecurityHeaders → CORS → SlowAPI → app
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        # X-Requested-With is required by cookie CSRF checks (app/core/csrf.py).
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    if not settings.is_development and settings.trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        )

    @app.get("/health")
    async def health_check() -> JSONResponse:
        # Milestone 3.1, Phase 23: a real dependency check, not a static
        # "ok" -- the only dependency this app actually has is Postgres, so
        # a cheap SELECT 1 is the whole check. 503 (not 200-with-a-body-
        # field) on failure so a load balancer/orchestrator's own health
        # check semantics work without it needing to parse the body.
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 -- any DB failure means "unhealthy", not a 500
            logger.exception("Health check failed: database unreachable")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "checks": {"database": "error"}},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok", "checks": {"database": "ok"}})

    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
