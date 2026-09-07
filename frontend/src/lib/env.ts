/**
 * Fails loud at import time if required public env vars are missing.
 *
 * NEXT_PUBLIC_API_URL must be the same-origin proxy path (`/api/backend`),
 * not `http://localhost:8000`. Cross-origin cookies break session restore
 * on reload — see next.config.ts rewrites and .env.local.example.
 */
function requireEnv(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `Missing required environment variable ${name}. Copy .env.local.example to .env.local and fill it in.`
    )
  }
  return value
}

export const API_BASE_URL = requireEnv("NEXT_PUBLIC_API_URL", process.env.NEXT_PUBLIC_API_URL)
