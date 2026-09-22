import type { Metadata } from "next"

import { InsightsIndexClient } from "@/components/insights/InsightsIndexClient"

export const metadata: Metadata = {
  title: "Insights",
  description: "Plain-language explainers on what your FaceIQ report measures, and how to get the most accurate one.",
}

export default function InsightsPage() {
  return <InsightsIndexClient />
}
