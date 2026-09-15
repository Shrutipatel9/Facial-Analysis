import { cn } from "@/lib/utils"

/** Outer muted frame with left/right breathing room (Report / AI Visuals). */
export function workspaceShellClassName() {
  return "flex h-full min-h-0 w-full flex-1 overflow-hidden bg-[#eef1f3] px-5 py-4 sm:px-8 sm:py-5 lg:px-10 lg:py-6"
}

/** Single white rounded container that wraps sidenav + content. */
export function workspaceUnifiedPanelClassName() {
  return "flex min-h-0 w-full flex-1 overflow-hidden rounded-2xl border border-black/[0.06] bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
}

/** Left ToC column inside the unified panel. */
export function workspaceAsideClassName() {
  return "hidden h-full w-[16.5rem] shrink-0 overflow-y-auto border-r border-border/80 px-3 py-4 sm:px-4 sm:py-5 lg:block"
}

export function workspaceAsideHeader(label: string) {
  return (
    <p className="px-2 pt-1 pb-3 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground/75 uppercase">
      {label}
    </p>
  )
}

/** Scrollable main content inside the unified panel. */
export function workspacePanelScrollClassName() {
  return "min-h-0 flex-1 overflow-y-auto overscroll-contain px-8 py-8 sm:px-11 sm:py-9 lg:px-12 lg:py-10"
}

/** Soft mint pill — active nav item. */
export function workspaceNavItemClassName(isActive: boolean) {
  return cn(
    "flex w-full items-center gap-2 rounded-full px-3.5 py-2 text-left text-[13px] transition-colors",
    isActive
      ? "bg-primary/15 font-medium text-primary"
      : "font-normal text-muted-foreground hover:bg-black/[0.03] hover:text-foreground"
  )
}

export function workspaceGroupToggleClassName() {
  return "flex w-full items-center justify-between rounded-md px-3.5 py-2 text-left text-[13px] font-medium text-foreground/90 transition-colors hover:bg-black/[0.03]"
}

/** @deprecated Prefer workspaceUnifiedPanelClassName for Report/AI Visuals. */
export function workspacePanelClassName() {
  return workspaceUnifiedPanelClassName()
}
