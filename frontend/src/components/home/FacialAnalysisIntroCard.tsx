"use client"

import { FEATURE_LABELS, FEATURE_ORDER } from "@/lib/report/reportFeatures"
import type { ReportOut } from "@/lib/reports/reportApi"

/**
 * Left-column “Your Facial Analysis” card -- short plain-language overview
 * derived from this report (face shape, focus areas, strengths / finding).
 * No photo, no static boilerplate, no numeric scores.
 */
export function FacialAnalysisIntroCard({ report }: { report: ReportOut }) {
  const { lead, detail, closing } = buildPlainOverview(report)

  return (
    <div className="flex h-fit w-full flex-col gap-3 rounded-2xl border border-border/80 bg-card p-5 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <h2 className="font-heading text-lg font-semibold tracking-tight text-primary">
        Your <span className="text-foreground">Facial Analysis</span>
      </h2>
      <div className="space-y-2.5 text-sm leading-relaxed text-muted-foreground">
        <p>{lead}</p>
        {detail ? <p>{detail}</p> : null}
        {closing ? <p>{closing}</p> : null}
      </div>
    </div>
  )
}

/** Builds short descriptive paragraphs from real report fields. */
function buildPlainOverview(report: ReportOut): { lead: string; detail: string | null; closing: string | null } {
  const { full } = report

  const scored = FEATURE_ORDER.map((feature) => {
    const entry = full.feature_scores[feature]
    if (!entry?.available || entry.score === null) return null
    return {
      feature,
      score: entry.score,
      finding: entry.finding,
      callout: full.features[feature]?.summary_callout ?? null,
      strengths: full.features[feature]?.strengths ?? null,
    }
  }).filter((entry): entry is NonNullable<typeof entry> => entry !== null)

  const priorities = [...scored].sort((a, b) => a.score - b.score)
  const strengths = [...scored].sort((a, b) => b.score - a.score)

  const faceShape = full.facial_assessments.face_shape
  const symmetry = full.facial_assessments.symmetry
  const proportions = full.facial_assessments.proportions

  const leadParts: string[] = []
  if (faceShape?.available && faceShape.label) {
    leadParts.push(`Your face shape reads as ${softenLabel(faceShape.label)}`)
  }
  if (symmetry?.available && symmetry.label) {
    leadParts.push(`with ${softenLabel(symmetry.label)} overall symmetry`)
  } else if (proportions?.available && proportions.label) {
    leadParts.push(`with ${softenLabel(proportions.label)} facial proportions`)
  }
  const lead =
    leadParts.length > 0
      ? `${leadParts.join(", ")}.`
      : "This overview brings together your facial proportions, feature balance, and a clear path for gentle refinement."

  let detail: string | null = null
  if (priorities.length >= 2) {
    const a = FEATURE_LABELS[priorities[0].feature].toLowerCase()
    const b = FEATURE_LABELS[priorities[1].feature].toLowerCase()
    const finding = priorities[0].finding || priorities[0].callout
    detail = finding
      ? `The clearest places to refine first are your ${a} and ${b}. ${stripNumerics(toOneSentence(finding))}`
      : `The clearest places to refine first are your ${a} and ${b}, where small adjustments can improve overall harmony.`
  } else if (priorities.length === 1) {
    const a = FEATURE_LABELS[priorities[0].feature].toLowerCase()
    const finding = priorities[0].finding || priorities[0].callout
    detail = finding
      ? `The clearest place to refine first is your ${a}. ${stripNumerics(toOneSentence(finding))}`
      : `The clearest place to refine first is your ${a}.`
  }

  let closing: string | null = null
  if (strengths.length >= 2) {
    const a = FEATURE_LABELS[strengths[0].feature].toLowerCase()
    const b = FEATURE_LABELS[strengths[1].feature].toLowerCase()
    closing = `Your ${a} and ${b} already read as relative strengths, so the protocol builds around those while addressing the softer areas.`
  } else if (strengths.length === 1) {
    const a = FEATURE_LABELS[strengths[0].feature].toLowerCase()
    closing = `Your ${a} already reads as a relative strength, so the protocol builds around that while addressing softer areas.`
  } else if (full.closing_recommendations) {
    closing = stripNumerics(toOneSentence(full.closing_recommendations))
  }

  return { lead, detail, closing }
}

function softenLabel(label: string): string {
  const trimmed = label.trim()
  if (!trimmed) return "balanced"
  return trimmed.charAt(0).toLowerCase() + trimmed.slice(1)
}

function toOneSentence(text: string): string {
  const cleaned = text.trim().replace(/\s+/g, " ")
  const match = cleaned.match(/^.*?[.!?](?:\s|$)/)
  const sentence = (match ? match[0] : cleaned).trim()
  return sentence.endsWith(".") || sentence.endsWith("!") || sentence.endsWith("?")
    ? sentence
    : `${sentence}.`
}

function stripNumerics(text: string): string {
  return text
    .replace(/\b\d+(\.\d+)?\s*%/g, "")
    .replace(/\b\d+(\.\d+)?\s*\/\s*\d+\b/g, "")
    .replace(/\b\d+(\.\d+)?\b/g, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([,.;:!?])/g, "$1")
    .trim()
}
