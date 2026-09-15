import { cn } from "@/lib/utils"

/** Shared settings content shell — left-aligned header + optional card body. */
export function SettingsSectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-1">
      <h2 className="font-heading text-xl font-semibold tracking-tight text-foreground">{title}</h2>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

export function SettingsCard({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border/80 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:p-6",
        className
      )}
    >
      {children}
    </div>
  )
}
