"use client"

import { Download, FileText, LayoutDashboard, Loader2, MessageSquare, Sparkles } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"

import { Logo } from "@/components/branding/Logo"
import { UserMenu } from "@/components/layout/UserMenu"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { downloadReportPdf } from "@/lib/reports/downloadReportPdf"
import * as reportApi from "@/lib/reports/reportApi"
import { cn } from "@/lib/utils"
import { useReportStore } from "@/store/reportStore"

const WORKSPACE_LINKS = [
  { href: "/home", label: "Dashboard", icon: LayoutDashboard },
  { href: "/report", label: "Report", icon: FileText },
  { href: "/ai-visuals", label: "AI Visuals", icon: Sparkles },
  { href: "/chat", label: "Chat Assistant", icon: MessageSquare },
] as const

/**
 * Post-report workspace header matching the Milestone 2 reference structure
 * (FR-018–FR-021): Logo · Report / AI Visuals / Chat · PDF · account.
 * FaceIQ branding stays; layout/behavior mirrors the reference nav, not its
 * name or copy (milestone2_requirements.md branding note).
 */
export function AppNavbar({ hasReport }: { hasReport: boolean }) {
  const pathname = usePathname()
  // PDF download stays available from both Home Overview and the
  // interactive Report (milestone2_home_and_report_spec.md §1.1/§0).
  const showPdf = hasReport && (pathname === "/home" || pathname === "/report")

  return (
    <header className="z-40 shrink-0 border-b border-border/70 bg-white">
      <div className="flex h-14 items-center gap-4 px-4 sm:gap-6 sm:px-6 lg:px-8">
        <Logo href="/home" size="md" className="text-[1.35rem] tracking-tight" />

        {hasReport ? (
          <nav className="hidden items-center gap-1 md:flex" aria-label="Workspace">
            {WORKSPACE_LINKS.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href || pathname.startsWith(`${href}/`)
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "inline-flex h-9 items-center gap-2 rounded-full px-3.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/12 text-primary"
                      : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                  )}
                >
                  <Icon className="size-3.5 shrink-0" strokeWidth={2} aria-hidden />
                  {label}
                </Link>
              )
            })}
          </nav>
        ) : null}

        <div className="ml-auto flex items-center gap-2 sm:gap-2.5">
          {showPdf ? <PdfNavButton /> : null}

          <UserMenu variant="workspace" />
        </div>
      </div>

      {hasReport ? (
        <nav
          className="flex gap-1 overflow-x-auto border-t border-border/60 px-3 py-2 md:hidden"
          aria-label="Workspace"
        >
          {WORKSPACE_LINKS.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname.startsWith(`${href}/`)
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs font-medium",
                  isActive
                    ? "bg-primary/12 text-primary"
                    : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                )}
              >
                <Icon className="size-3.5" aria-hidden />
                {label}
              </Link>
            )
          })}
        </nav>
      ) : null}
    </header>
  )
}

function PdfNavButton() {
  const report = useReportStore((state) => state.report)
  const [isDownloading, setIsDownloading] = useState(false)

  async function handleDownload() {
    setIsDownloading(true)
    try {
      let reportId = report?.id
      let createdAt = report?.created_at
      if (!reportId || !createdAt) {
        const summaries = await reportApi.listReports()
        const latest = summaries[0]
        if (!latest) {
          toast.error("No report available to download yet.")
          return
        }
        reportId = latest.id
        createdAt = latest.created_at
      }
      await downloadReportPdf(reportId, createdAt)
      toast.success("PDF downloaded.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={() => void handleDownload()}
      disabled={isDownloading}
      className={cn(
        "inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-full bg-primary px-3.5 text-sm font-medium text-primary-foreground transition",
        "hover:bg-primary/90 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
        "disabled:pointer-events-none disabled:opacity-60"
      )}
      aria-label="Download PDF"
    >
      {isDownloading ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" aria-hidden />}
      <span className="hidden sm:inline">PDF</span>
    </button>
  )
}
