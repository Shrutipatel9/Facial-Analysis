"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

import { BrandLoader } from "@/components/branding/BrandLoader"

/**
 * Legacy route. Post-analysis home is `/home` (Home Overview, see
 * docs/milestone2_home_and_report_spec.md §0.1) -- never re-render the old
 * Milestone 1 Welcome dashboard here. Keep this path as a hard redirect so
 * bookmarks/old links still work.
 */
export default function DashboardRedirectPage() {
  const router = useRouter()

  useEffect(() => {
    router.replace("/home")
  }, [router])

  return <BrandLoader />
}
