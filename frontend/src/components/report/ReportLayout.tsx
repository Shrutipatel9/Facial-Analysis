"use client"

import { useRef } from "react"

import { ReportNav } from "./ReportNav"
import {
  workspaceAsideClassName,
  workspacePanelScrollClassName,
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

        <div ref={scrollContainerRef} className={workspacePanelScrollClassName()}>
          {children}
        </div>
      </div>
    </section>
  )
}
