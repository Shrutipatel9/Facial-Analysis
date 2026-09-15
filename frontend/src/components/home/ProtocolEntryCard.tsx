import { ArrowRight } from "lucide-react"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { formatDate } from "@/lib/format"
import type { ReportOut } from "@/lib/reports/reportApi"

/**
 * Home Overview left-column protocol CTA (spec §1.3) -- dark entry card
 * matching the reference’s “New / VIEW FULL REPORT” block. No fabricated
 * protocol number (none exists in the data model).
 */
export function ProtocolEntryCard({ report }: { report: ReportOut }) {
  return (
    <div className="flex h-fit w-full flex-col items-center justify-center gap-4 rounded-2xl bg-slate-700 px-5 py-8 text-center text-white shadow-[0_10px_30px_-18px_rgba(20,55,75,0.35)]">
      <div className="space-y-1">
        <p className="text-2xl font-semibold tracking-tight">New</p>
        <p className="text-xs font-medium tracking-[0.14em] text-white/70 uppercase">
          FACIAL ANALYSIS · {formatDate(report.created_at)}
        </p>
      </div>
      <Button
        className="h-9 rounded-full border-0 bg-white/15 px-5 text-xs font-semibold tracking-[0.08em] text-white uppercase hover:bg-white/25"
        render={<Link href="/report" />}
        nativeButton={false}
      >
        View Full Report
        <ArrowRight className="size-3.5" />
      </Button>
    </div>
  )
}
