"use client"

import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"

import { AgingView } from "./AgingView"
import { HairstyleView } from "./HairstyleView"
import { OutfitView } from "./OutfitView"
import {
  workspaceAsideClassName,
  workspaceAsideHeader,
  workspaceGroupToggleClassName,
  workspaceNavItemClassName,
  workspacePanelScrollClassName,
  workspaceShellClassName,
  workspaceUnifiedPanelClassName,
} from "@/components/layout/workspaceChrome"
import type { AiVisualKind } from "@/lib/aiVisuals/aiVisualsApi"

const NAV_ITEMS: { kind: AiVisualKind; label: string }[] = [
  { kind: "hairstyle", label: "Hairstyle previews" },
  { kind: "outfit", label: "Outfit styles" },
  { kind: "aging", label: "Healthy aging" },
]

/**
 * AI Visuals: same unified padded container as Report (sidenav + content).
 */
export function AiVisualsLayout() {
  const [activeKind, setActiveKind] = useState<AiVisualKind>("hairstyle")
  const [previewsOpen, setPreviewsOpen] = useState(true)

  return (
    <section className={workspaceShellClassName()}>
      <div className={workspaceUnifiedPanelClassName()}>
        <aside className={workspaceAsideClassName()}>
          {workspaceAsideHeader("AI Visuals")}
          <nav className="flex flex-col gap-1 pb-4" aria-label="AI Visuals sections">
            <button
              type="button"
              onClick={() => setPreviewsOpen((open) => !open)}
              className={workspaceGroupToggleClassName()}
              aria-expanded={previewsOpen}
            >
              <span>Previews</span>
              {previewsOpen ? (
                <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              ) : (
                <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              )}
            </button>
            {previewsOpen
              ? NAV_ITEMS.map((item) => {
                  const isActive = item.kind === activeKind
                  return (
                    <button
                      key={item.kind}
                      type="button"
                      onClick={() => setActiveKind(item.kind)}
                      className={workspaceNavItemClassName(isActive)}
                      aria-current={isActive ? "true" : undefined}
                    >
                      {item.label}
                    </button>
                  )
                })
              : null}
          </nav>
        </aside>

        <div className={workspacePanelScrollClassName()}>
          {activeKind === "hairstyle" ? <HairstyleView /> : null}
          {activeKind === "outfit" ? <OutfitView /> : null}
          {activeKind === "aging" ? <AgingView /> : null}
        </div>
      </div>
    </section>
  )
}
