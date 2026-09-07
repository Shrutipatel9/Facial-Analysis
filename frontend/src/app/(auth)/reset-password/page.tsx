import { Suspense } from "react"

import { ResetPasswordClient } from "./ResetPasswordClient"

export const metadata = {
  title: "Reset password",
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordClient />
    </Suspense>
  )
}
