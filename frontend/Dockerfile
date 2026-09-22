# Milestone 3.1, Phase 25 (production hardening) -- platform-agnostic,
# Docker-based build. Deployment target is deliberately undecided (see
# docs/deployment.md). Standard Next.js standalone-output multi-stage
# pattern -- deps / build / runtime kept as separate stages/layers so an
# app-code-only change doesn't invalidate the (slow) npm ci layer.

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci


FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* vars get inlined into the client bundle at build time (src/
# lib/env.ts fails the build loudly if unset -- confirmed the hard way: an
# earlier version of this Dockerfile only set NEXT_PUBLIC_API_URL at
# runtime, which is too late for a NEXT_PUBLIC_* var and broke `next
# build`'s static prerender). Defaulted here, not left to the caller to
# supply, because this value is architecturally fixed for this app (the
# same-origin proxy path -- see next.config.ts's rewrite and .env.local.
# example's own "do NOT point this at http://localhost:8000" warning), not
# a per-deploy secret.
ARG NEXT_PUBLIC_API_URL=/api/backend
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
# BACKEND_URL only matters at runtime (next.config.ts's rewrite target) --
# no build-time secret/URL is baked into the image for this one.
RUN npm run build


FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production

RUN groupadd --system app && useradd --system --gid app --no-create-home app

# .next/standalone already contains its own minimal node_modules subset
# (Next.js traces exactly what's needed) -- the full node_modules from the
# deps/builder stages never reaches this final image.
COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static
COPY --from=builder --chown=app:app /app/public ./public

USER app

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
