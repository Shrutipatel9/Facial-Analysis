"use client"

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts"

import { HARMONY_AXES } from "@/lib/reports/reportApi"

const AXIS_LABELS: Record<(typeof HARMONY_AXES)[number], string> = {
  harmony: "Harmony",
  symmetry: "Symmetry",
  smoothness: "Smoothness",
  jawline: "Jawline",
  skin: "Skin",
  volume: "Volume",
}

/**
 * Dashboard's 6-axis Harmony chart (Milestone 2) -- all 6 axes are
 * first-pass heuristic scores (facial_assessment_service.compute_harmony_chart),
 * not clinically calibrated; presented as a visual summary, not a precise
 * measurement. No locked/unlocked pre-payment state -- a Report can only
 * ever exist already-paid (see report-enrichment/plans.md decision 5).
 * Uses the dashboard's own --primary token (not the report page's Meridian
 * skin, which is scoped to report/facial-assessment cards only).
 */
export function HarmonyRadarChart({
  harmonyChart,
  heightClassName = "h-64",
}: {
  harmonyChart: Record<string, number | null>
  /** Tailwind height class -- lets the Dashboard's promoted ReportHero
   * render this larger than the original card's fixed h-64. */
  heightClassName?: string
}) {
  const data = HARMONY_AXES.map((axis) => ({
    axis: AXIS_LABELS[axis],
    value: harmonyChart[axis] ?? 0,
    available: harmonyChart[axis] !== null && harmonyChart[axis] !== undefined,
  }))
  const hasAnyValue = data.some((entry) => entry.available)

  if (!hasAnyValue) {
    return <p className="text-sm text-muted-foreground">Harmony chart isn&apos;t available for this report yet.</p>
  }

  return (
    <div className={`${heightClassName} w-full`}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="75%">
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
          <Radar
            dataKey="value"
            stroke="var(--primary)"
            fill="var(--primary)"
            fillOpacity={0.22}
            isAnimationActive={false}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
