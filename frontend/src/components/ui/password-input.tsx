"use client"

import { Eye, EyeOff } from "lucide-react"
import * as React from "react"

import { cn } from "cn"

import { Input } from "@/components/ui/input"

/**
 * A password Input with a show/hide toggle. Forwards refs/props exactly
 * like Input so it drops into the FormControl -> react-hook-form Controller
 * pattern the same way (see components/ui/form.tsx's FormControl, which
 * clones id/aria-* onto whatever single child it's given).
 */
const PasswordInput = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, ...props }, ref) => {
    const [visible, setVisible] = React.useState(false)

    return (
      <div className="relative">
        <Input ref={ref} type={visible ? "text" : "password"} className={cn("pr-11", className)} {...props} />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none"
        >
          {visible ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
        </button>
      </div>
    )
  }
)
PasswordInput.displayName = "PasswordInput"

export { PasswordInput }
