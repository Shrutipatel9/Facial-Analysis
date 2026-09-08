import { Suspense } from "react"

import { ResetPasswordConfirmClient } from "./ResetPasswordConfirmClient"

export const metadata = {
  title: "Set new password",
}

export default function ResetPasswordConfirmPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordConfirmClient />
    </Suspense>
  )
}
