"use client"

import { Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { meridian } from "@/lib/report/meridianTokens"
import * as reportApi from "@/lib/reports/reportApi"

/**
 * Milestone 2 (FR-022) -- renders per `visualStatus`, exactly the 5
 * reachable states (report_enrichment/plans.md decision 5: no locked/
 * unlocked pre-payment state, since a Report can only ever exist already
 * paid). The AI-disclosure band on `generated` is mandatory and
 * deliberately the loudest element on the card -- report_design_spec.md
 * §9.1's Category-C rule breaks the accent-scarcity rule on purpose so an
 * AI-generated image is never mistaken for an original photo.
 */
export function BeforeAfterBlock({
  reportId,
  feature,
  featureLabel,
  visualStatus,
  beforeImageUrl,
}: {
  reportId: string
  feature: string
  featureLabel: string
  visualStatus: string
  beforeImageUrl: string | undefined
}) {
  const [afterUrl, setAfterUrl] = useState<string | null>(null)
  const fetchedFor = useRef<string | null>(null)

  useEffect(() => {
    if (visualStatus !== "generated") return
    const key = `${reportId}/${feature}`
    if (fetchedFor.current === key) return
    fetchedFor.current = key

    // No cancelled-flag guard on the setAfterUrl call itself -- combined
    // with the fetchedFor ref above, one would silently discard a Strict
    // Mode dev double-invoke's real (second) result: the ref survives the
    // mount/cleanup/remount cycle and blocks the second effect run, while
    // a cancelled check would discard the first run's now-late response.
    // Matches ReportScreen.tsx's imagesFetchedFor convention.
    let objectUrl: string | null = null
    reportApi
      .getFeatureVisual(reportId, feature)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setAfterUrl(objectUrl)
      })
      .catch(() => {})

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [reportId, feature, visualStatus])

  if (visualStatus === "not_attempted") {
    return null
  }

  if (visualStatus === "pending" || visualStatus === "generating") {
    return (
      <div
        className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs"
        style={{ backgroundColor: meridian.surface.recessed, color: meridian.ink.muted }}
      >
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        AI visualization is generating -- check back shortly.
      </div>
    )
  }

  if (visualStatus === "failed") {
    return (
      <p className="rounded-lg px-3 py-2 text-xs" style={{ backgroundColor: meridian.surface.recessed, color: meridian.ink.muted }}>
        The AI visualization for this feature couldn&apos;t be generated. The rest of your report is unaffected.
      </p>
    )
  }

  if (!afterUrl) {
    return (
      <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs" style={{ color: meridian.ink.muted }}>
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        Loading visualization…
      </div>
    )
  }

  return (
    <div
      className="w-fit max-w-full overflow-hidden rounded-xl"
      style={{ border: `1px solid ${meridian.surface.recessed}` }}
    >
      <div className="grid grid-cols-2" style={{ backgroundColor: meridian.surface.recessed }}>
        <figure className="m-0 flex flex-col items-center">
          {beforeImageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL
            <img
              src={beforeImageUrl}
              alt={`${featureLabel} before`}
              className="h-36 w-auto max-w-[9.5rem] object-contain sm:h-40 sm:max-w-[10.5rem]"
            />
          ) : (
            <div className="flex h-36 w-28 items-center justify-center sm:h-40" />
          )}
          <figcaption
            className="w-full py-1.5 text-center text-[10px] font-medium tracking-[0.08em] uppercase"
            style={{ backgroundColor: meridian.surface.card, color: meridian.ink.muted }}
          >
            Before
          </figcaption>
        </figure>
        <figure
          className="m-0 flex flex-col items-center border-l"
          style={{ borderColor: meridian.surface.recessed }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL */}
          <img
            src={afterUrl}
            alt={`${featureLabel} after, AI-generated`}
            className="h-36 w-auto max-w-[9.5rem] object-contain sm:h-40 sm:max-w-[10.5rem]"
          />
          <figcaption
            className="w-full py-1.5 text-center text-[10px] font-medium tracking-[0.08em] uppercase"
            style={{ backgroundColor: meridian.surface.card, color: meridian.ink.muted }}
          >
            After
          </figcaption>
        </figure>
      </div>
      <div
        className="px-3 py-1.5 text-center text-[11px] font-medium"
        style={{ backgroundColor: meridian.accent.primary, color: meridian.surface.card }}
      >
        AI-generated visualization -- not a medical prediction or guaranteed outcome
      </div>
    </div>
  )
}
