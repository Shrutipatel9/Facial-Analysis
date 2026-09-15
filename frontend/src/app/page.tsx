"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { BrandLoader } from "@/components/branding/BrandLoader"
import { LandingPage } from "@/components/landing/LandingPage"
import { useAuthStore } from "@/store/authStore"

/**
 * Marketing landing for signed-out visitors. Authenticated users go to
 * /home (Home Overview); incomplete onboarding is redirected by the
 * protected guards.
 */
export default function RootPage() {
  const status = useAuthStore((state) => state.status)
  const router = useRouter()

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/home")
    }
  }, [status, router])

  if (status === "idle" || status === "authenticated") {
    return <BrandLoader />
  }

  return <LandingPage />
}
