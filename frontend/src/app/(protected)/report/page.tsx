import { Suspense } from "react"

import { ReportScreen } from "@/components/report/ReportScreen"

export const metadata = {
  title: "Your report",
}

export default function ReportPage() {
  return (
    <Suspense fallback={null}>
      <ReportScreen />
    </Suspense>
  )
}
