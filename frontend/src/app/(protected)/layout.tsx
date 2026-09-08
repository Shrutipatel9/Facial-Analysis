"use client"

import { motion } from "motion/react"
import { usePathname } from "next/navigation"

import { BrandLoader } from "@/components/branding/BrandLoader"
import { Logo } from "@/components/branding/Logo"
import { UserMenu } from "@/components/layout/UserMenu"
import { useAuthGuard } from "@/hooks/useAuthGuard"
import { usePhotoUploadGuard } from "@/hooks/usePhotoUploadGuard"
import { useQuestionnaireGuard } from "@/hooks/useQuestionnaireGuard"
import { cn } from "@/lib/utils"

const FULL_BLEED = new Set(["/dashboard", "/questionnaire", "/photos"])

export default function ProtectedRouteGroupLayout({ children }: { children: React.ReactNode }) {
  const { isChecking: isAuthChecking } = useAuthGuard()
  const { isChecking: isQuestionnaireChecking } = useQuestionnaireGuard(!isAuthChecking)
  const { isChecking: isPhotoChecking } = usePhotoUploadGuard(!isAuthChecking && !isQuestionnaireChecking)
  const isChecking = isAuthChecking || isQuestionnaireChecking || isPhotoChecking
  const pathname = usePathname()
  const isFullBleed = FULL_BLEED.has(pathname)

  if (isChecking) {
    return <BrandLoader />
  }

  return (
    <div
      className={cn(
        // isolate keeps -z-10 orbs inside this shell (avoids black peek-through
        // in scrollbar gutters). overflow-x-hidden kills the horizontal bar.
        "relative isolate flex flex-col overflow-x-hidden bg-[#f1f4f6]",
        // Full-bleed: one viewport shell; only main scrolls when content overflows.
        isFullBleed ? "h-svh overflow-y-hidden" : "min-h-svh"
      )}
    >
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
        <div className="absolute top-[-20%] left-[-10%] h-[28rem] w-[28rem] rounded-full bg-primary/[0.07] blur-3xl" />
        <div className="absolute right-[-8%] bottom-[-15%] h-[24rem] w-[24rem] rounded-full bg-primary/[0.05] blur-3xl" />
      </div>

      <motion.header
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="z-40 shrink-0 border-b border-primary/10 bg-primary/[0.07] backdrop-blur-xl"
      >
        <div className="flex h-14 items-center justify-between px-5 sm:px-8">
          <Logo href="/dashboard" size="md" />
          <UserMenu />
        </div>
      </motion.header>

      <motion.main
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className={cn(
          "relative flex min-h-0 flex-1 flex-col",
          // auto = scrollbar only when content actually overflows; never force both axes
          isFullBleed && "overflow-x-hidden overflow-y-auto",
          !isFullBleed && "mx-auto w-full max-w-6xl px-6 py-10 sm:py-12"
        )}
      >
        {children}
      </motion.main>
    </div>
  )
}
