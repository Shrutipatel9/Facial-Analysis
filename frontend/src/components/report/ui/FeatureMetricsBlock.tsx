"use client"

import { useState } from "react"
import { formatMetricValue, humanizeMetricKey } from "@/lib/report/metricLabels"
import { meridian } from "@/lib/report/meridianTokens"
import type { ReportMeasurement } from "@/lib/reports/reportApi"

// Phase 14 (Milestone 3, FR-023) -- with more metrics per feature, the
// "All metrics" list below would otherwise be a wall of 8-11+ rows.
// Collapsed by default past this many rows, same boolean-toggle pattern
// as ReportNav.tsx's openGroups state.
const COLLAPSED_ROW_COUNT = 6

/**
 * Feature metrics: small label/value cards + wider featured metric (screenshot layout).
 */
export function FeatureMetricsBlock({ measurement }: { measurement: ReportMeasurement }) {
  const [expanded, setExpanded] = useState(false)

  if (!measurement.available || !measurement.metrics || Object.keys(measurement.metrics).length === 0) {
    return measurement.note ? (
      <p className="text-xs leading-relaxed" style={{ color: meridian.ink.muted }}>
        {measurement.note}
      </p>
    ) : null
  }

  const entries = Object.entries(measurement.metrics)
  const [featured, ...rest] = entries
  const gridEntries = rest.slice(0, 4)
  const visibleEntries = expanded ? entries : entries.slice(0, COLLAPSED_ROW_COUNT)
  const hiddenCount = entries.length - visibleEntries.length

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        {gridEntries.map(([key, value]) => (
          <div
            key={key}
            className="rounded-xl border border-border/80 bg-white px-3.5 py-3"
          >
            <p
              className="text-[10px] font-semibold tracking-[0.12em] uppercase"
              style={{ color: meridian.ink.muted }}
            >
              {humanizeMetricKey(key)}
            </p>
            <p className="mt-1.5 text-base font-semibold tabular-nums" style={{ color: meridian.ink.primary }}>
              {formatMetricValue(value)}
            </p>
          </div>
        ))}
        <div
          className="col-span-2 rounded-xl border border-border/80 bg-white px-4 py-3 sm:col-span-2 lg:col-span-2"
          style={{ backgroundColor: meridian.surface.recessed }}
        >
          <p className="text-sm font-semibold" style={{ color: meridian.ink.primary }}>
            {humanizeMetricKey(featured[0])}
          </p>
          <p className="mt-3 text-3xl font-semibold tabular-nums" style={{ color: meridian.ink.primary }}>
            {formatMetricValue(featured[1])}
          </p>
          <p
            className="mt-2 text-[10px] font-semibold tracking-[0.12em] uppercase"
            style={{ color: meridian.ink.muted }}
          >
            Landmark-based
          </p>
        </div>
      </div>

      {entries.length > 0 ? (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold" style={{ color: meridian.ink.primary }}>
            All {humanizeMetricKey(featured[0]).split(" ")[0]} metrics
          </h4>
          <dl className="grid grid-cols-1 gap-x-10 gap-y-2 sm:grid-cols-2">
            {visibleEntries.map(([key, value]) => (
              <div key={key} className="flex items-baseline justify-between gap-3 border-b border-border/50 py-1.5">
                <dt className="text-sm" style={{ color: meridian.accent.secondary }}>
                  {humanizeMetricKey(key)}
                </dt>
                <dd className="text-sm font-semibold tabular-nums" style={{ color: meridian.ink.primary }}>
                  {formatMetricValue(value)}
                </dd>
              </div>
            ))}
          </dl>
          {hiddenCount > 0 || expanded ? (
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="text-xs font-semibold tracking-wide"
              style={{ color: meridian.accent.secondary }}
            >
              {expanded ? "Show less" : `Show ${hiddenCount} more metric${hiddenCount === 1 ? "" : "s"}`}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
