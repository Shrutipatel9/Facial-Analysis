import { Suspense } from "react"

import { HomeOverviewScreen } from "@/components/home/HomeOverviewScreen"

export const metadata = {
  title: "Home",
}

export default function HomePage() {
  return (
    <Suspense fallback={null}>
      <HomeOverviewScreen />
    </Suspense>
  )
}
