"use client"

import { useRef } from "react"

import { ReportNav } from "./ReportNav"
import {
  workspaceAsideClassName,
  workspaceShellClassName,
  workspaceUnifiedPanelClassName,
} from "@/components/layout/workspaceChrome"

/**
 * Report shell: one shared rounded container holds padded sidenav + content.
 */
export function ReportLayout({ children }: { children: React.ReactNode }) {
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  return (
    <section className={workspaceShellClassName()}>
      <div className={workspaceUnifiedPanelClassName()}>
        <aside className={workspaceAsideClassName()}>
          <ReportNav scrollContainerRef={scrollContainerRef} />
        </aside>

        <div
          ref={scrollContainerRef}
          className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-6 sm:px-7 sm:py-7 lg:px-8"
        >
          {children}
        </div>
      </div>
    </section>
  )
}
