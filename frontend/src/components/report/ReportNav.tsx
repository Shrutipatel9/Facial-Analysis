"use client"

import { ChevronDown, ChevronRight } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import {
  workspaceAsideHeader,
  workspaceGroupToggleClassName,
  workspaceNavItemClassName,
} from "@/components/layout/workspaceChrome"
import { FEATURE_LABELS, FEATURE_ORDER, assessmentAnchorId, featureAnchorId } from "@/lib/report/reportFeatures"
import { ASSESSMENT_LABELS, ASSESSMENT_ORDER } from "@/lib/reports/reportApi"
import { cn } from "@/lib/utils"

type NavItem = { id: string; label: string }

type NavGroup = {
  id: string
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    id: "group-introduction",
    label: "Introduction",
    items: [
      { id: "introduction", label: "Introduction" },
      { id: "disclaimer", label: "Disclaimer" },
    ],
  },
  {
    id: "group-assessments",
    label: "Facial Assessments",
    items: ASSESSMENT_ORDER.map((key) => ({
      id: assessmentAnchorId(key),
      label: ASSESSMENT_LABELS[key],
    })),
  },
  {
    id: "group-features",
    label: "Features Analysis",
    items: FEATURE_ORDER.map((feature) => ({
      id: featureAnchorId(feature),
      label: FEATURE_LABELS[feature],
    })),
  },
  {
    id: "group-protocol",
    label: "Protocol",
    items: [{ id: "protocol", label: "Treatment protocol" }],
  },
]

const ALL_ITEM_IDS = NAV_GROUPS.flatMap((group) => group.items.map((item) => item.id))

/**
 * Collapsible left ToC (screenshot match): group chevrons + mint pill active item.
 * Active highlight via IntersectionObserver on the content scroller.
 */
export function ReportNav({ scrollContainerRef }: { scrollContainerRef: React.RefObject<HTMLDivElement | null> }) {
  const [activeId, setActiveId] = useState<string>("introduction")
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(NAV_GROUPS.map((group) => [group.id, true]))
  )
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    const root = scrollContainerRef.current
    if (!root) return

    const visible = new Map<string, number>()
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            visible.set(entry.target.id, entry.intersectionRatio)
          } else {
            visible.delete(entry.target.id)
          }
        }
        if (visible.size === 0) return
        let bestId = activeId
        let bestRatio = -1
        for (const [id, ratio] of visible) {
          if (ratio > bestRatio) {
            bestRatio = ratio
            bestId = id
          }
        }
        setActiveId(bestId)
      },
      { root, threshold: [0.1, 0.25, 0.5, 0.75] }
    )
    observerRef.current = observer

    for (const id of ALL_ITEM_IDS) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }

    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- observed elements are static per report render
  }, [scrollContainerRef])

  // Keep the group that owns the active section expanded. Deferred via a
  // microtask, not called synchronously, to avoid a same-tick
  // setState-in-effect cascading render.
  useEffect(() => {
    void Promise.resolve().then(() => {
      const owner = NAV_GROUPS.find((group) => group.items.some((item) => item.id === activeId))
      if (!owner) return
      setOpenGroups((prev) => (prev[owner.id] ? prev : { ...prev, [owner.id]: true }))
    })
  }, [activeId])

  function handleClick(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  function toggleGroup(groupId: string) {
    setOpenGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }))
  }

  return (
    <nav className="flex h-full min-h-0 flex-col" aria-label="Report table of contents">
      {workspaceAsideHeader("Report")}
      <div className="flex flex-col gap-1.5 pb-4">
        {NAV_GROUPS.map((group) => {
          const isOpen = openGroups[group.id] !== false
          return (
            <div key={group.id} className="space-y-0.5">
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className={workspaceGroupToggleClassName()}
                aria-expanded={isOpen}
              >
                <span>{group.label}</span>
                {isOpen ? (
                  <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                ) : (
                  <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                )}
              </button>
              <div
                className={cn("space-y-0.5 overflow-hidden pl-1", isOpen ? "block" : "hidden")}
                role="group"
                aria-label={group.label}
              >
                {group.items.map((item) => {
                  const isActive = item.id === activeId
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleClick(item.id)}
                      className={workspaceNavItemClassName(isActive)}
                      aria-current={isActive ? "true" : undefined}
                    >
                      <span className="truncate">{item.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </nav>
  )
}
