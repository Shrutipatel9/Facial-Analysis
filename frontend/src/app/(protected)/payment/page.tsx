import { Suspense } from "react"

import { PaymentScreen } from "@/components/payment/PaymentScreen"

export const metadata = {
  title: "Unlock your analysis",
}

export default function PaymentPage() {
  return (
    <Suspense fallback={null}>
      <PaymentScreen />
    </Suspense>
  )
}
