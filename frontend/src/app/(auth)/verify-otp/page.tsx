import { Suspense } from "react"

import { VerifyOtpClient } from "./VerifyOtpClient"

export const metadata = {
  title: "Verify code",
}

export default function VerifyOtpPage() {
  return (
    <Suspense fallback={null}>
      <VerifyOtpClient />
    </Suspense>
  )
}
