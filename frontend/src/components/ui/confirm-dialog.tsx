"use client"

import { AlertTriangle, HelpCircle, Loader2, type LucideIcon } from "lucide-react"
import { type ReactElement, type ReactNode, useState } from "react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { cn } from "@/lib/utils"

type ConfirmVariant = "destructive" | "default"

interface ConfirmDialogProps {
  /** Optional when using controlled `open` / `onOpenChange`. */
  trigger?: ReactElement
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  variant?: ConfirmVariant
  icon?: LucideIcon
  onConfirm: () => void | Promise<void>
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

const VARIANT_STYLES: Record<ConfirmVariant, { iconWrap: string; icon: LucideIcon }> = {
  destructive: {
    iconWrap: "bg-destructive/10 text-destructive",
    icon: AlertTriangle,
  },
  default: {
    iconWrap: "bg-accent text-accent-foreground",
    icon: HelpCircle,
  },
}

/**
 * Standing project convention: every destructive/irreversible action goes
 * through this dialog — never fire directly on click.
 */
export function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "destructive",
  icon,
  onConfirm,
  open: openProp,
  onOpenChange,
}: ConfirmDialogProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false)
  const [isPending, setIsPending] = useState(false)

  const isControlled = openProp !== undefined
  const open = isControlled ? openProp : uncontrolledOpen

  function setOpen(next: boolean) {
    if (!isControlled) setUncontrolledOpen(next)
    onOpenChange?.(next)
  }

  const styles = VARIANT_STYLES[variant]
  const Icon = icon ?? styles.icon

  async function handleConfirm() {
    setIsPending(true)
    try {
      await onConfirm()
      setOpen(false)
    } finally {
      setIsPending(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => !isPending && setOpen(next)}>
      {trigger ? <AlertDialogTrigger render={trigger} /> : null}
      <AlertDialogContent size="sm" className="gap-0 overflow-hidden p-0 sm:max-w-[22rem]">
        <div className="flex flex-col items-center gap-4 px-6 pt-7 pb-5 text-center">
          <AlertDialogMedia className={cn("mb-0 size-12 rounded-full shadow-none ring-0", styles.iconWrap)}>
            <Icon className="size-5" aria-hidden />
          </AlertDialogMedia>
          <AlertDialogHeader className="place-items-center gap-2 text-center sm:place-items-center sm:text-center">
            <AlertDialogTitle className="text-lg font-semibold tracking-tight">{title}</AlertDialogTitle>
            {description ? (
              <AlertDialogDescription className="text-sm leading-relaxed text-muted-foreground">
                {description}
              </AlertDialogDescription>
            ) : null}
          </AlertDialogHeader>
        </div>
        <AlertDialogFooter className="mx-0 mb-0 grid grid-cols-2 gap-3 rounded-none border-t border-border bg-transparent p-4">
          <AlertDialogCancel disabled={isPending} className="w-full">
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            variant={variant === "destructive" ? "destructive" : "default"}
            disabled={isPending}
            className="w-full"
            onClick={handleConfirm}
          >
            {isPending ? <Loader2 className="size-4 animate-spin" /> : null}
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
