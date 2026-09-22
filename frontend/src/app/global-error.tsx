"use client"

import { useEffect } from "react"

/**
 * Milestone 3.1, Phase 24 (production hardening) -- catches an error
 * thrown by the root layout itself (app/layout.tsx), the one case
 * error.tsx can't cover (it's rendered *inside* the layout, so a layout-
 * level failure bypasses it). Must render its own complete <html>/<body>:
 * this replaces the root layout entirely when it triggers, so it can't
 * assume ThemeProvider/fonts/Toaster from layout.tsx are mounted. Kept
 * deliberately plain and dependency-free for that reason -- inline styles
 * only, no Tailwind/component imports that could themselves be part of
 * what broke.
 */
export default function GlobalError({ error }: { error: Error & { digest?: string } }) {
  useEffect(() => {
    console.error("Unhandled root layout error:", error)
  }, [error])

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100svh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1.5rem",
          padding: "4rem 1rem",
          textAlign: "center",
          fontFamily: "system-ui, -apple-system, sans-serif",
          background: "#fafafa",
          color: "#1a1a1a",
        }}
      >
        <div style={{ fontSize: "1.25rem", fontWeight: 600, letterSpacing: "-0.01em" }}>FaceIQ</div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: "24rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>Something went wrong</h1>
          <p style={{ fontSize: "0.875rem", color: "#666", margin: 0 }}>
            An unexpected error occurred loading this page. Please try reloading.
          </p>
          {error.digest ? (
            <p style={{ fontSize: "0.75rem", color: "#999", margin: 0 }}>Reference: {error.digest}</p>
          ) : null}
        </div>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: "0.5rem 1.25rem",
            borderRadius: "0.5rem",
            border: "none",
            background: "#1a1a1a",
            color: "#fff",
            fontSize: "0.875rem",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          Reload page
        </button>
      </body>
    </html>
  )
}
