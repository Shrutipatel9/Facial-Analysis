import type { NextConfig } from "next"

/**
 * Browser calls go to same-origin `/api/backend/*`. Next.js rewrites them to
 * the FastAPI server. That makes the httpOnly refresh cookie first-party on
 * the frontend origin so it survives reload / tab close / browser restart.
 */
const backendUrl = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "")
const isProd = process.env.NODE_ENV === "production"

/**
 * Practical CSP for Next.js App Router. `unsafe-inline` / `unsafe-eval` are
 * still required by the framework/tooling in many setups; tightening to
 * nonce-based CSP is a follow-up hardening step once deploy tooling supports
 * it. `connect-src 'self'` matches the same-origin `/api/backend` proxy.
 */
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "object-src 'none'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "worker-src 'self' blob:",
].join("; ")

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ]
  },
  async headers() {
    const securityHeaders = [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      {
        // camera=(self): the photo-capture flow uses getUserMedia() on this
        // origin (CameraCapture.tsx) -- an empty allowlist blocks that at
        // the document level even after the browser's own per-site camera
        // permission is granted, since Permissions-Policy is enforced
        // before that browser prompt/setting is consulted. Third-party
        // (embedded) origins still get no camera access either way.
        key: "Permissions-Policy",
        value: "camera=(self), microphone=(), geolocation=(), payment=()",
      },
      { key: "X-XSS-Protection", value: "0" },
      { key: "Content-Security-Policy", value: contentSecurityPolicy },
    ]

    if (isProd) {
      securityHeaders.push({
        key: "Strict-Transport-Security",
        value: "max-age=63072000; includeSubDomains; preload",
      })
    }

    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ]
  },
}

export default nextConfig
