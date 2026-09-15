import { cn } from "@/lib/utils"

/**
 * Constrains report overlay photos so they don’t stretch full-bleed
 * across the content pane (which made faces look zoomed-out / wide).
 */
export function ReportPhotoFrame({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("mx-auto w-full max-w-[18rem] overflow-hidden rounded-xl sm:max-w-[20rem]", className)}>
      {children}
    </div>
  )
}
