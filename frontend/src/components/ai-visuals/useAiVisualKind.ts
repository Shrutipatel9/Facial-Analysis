"use client"

import { useCallback, useEffect, useState } from "react"

import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as aiVisualsApi from "@/lib/aiVisuals/aiVisualsApi"
import type { AiVisual, AiVisualKind } from "@/lib/aiVisuals/aiVisualsApi"

const POLL_INTERVAL_MS = 3000

export function isRetryableFailureSet(variations: AiVisual[]): boolean {
  return (
    variations.length > 0 &&
    variations.every((v) => v.status === "failed") &&
    variations.every((v) => v.error_reason === "rate_limited" || v.error_reason === "timeout")
  )
}

/** Shared create → poll → optional retry for one AI Visuals kind. */
export function useAiVisualKind(kind: AiVisualKind) {
  const [variations, setVariations] = useState<AiVisual[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isRetrying, setIsRetrying] = useState(false)

  const load = useCallback(async () => {
    setErrorMessage(null)
    const rows = await aiVisualsApi.createVisuals(kind)
    setVariations(rows)
  }, [kind])

  useEffect(() => {
    void load().catch((err) => setErrorMessage(getErrorMessage(err)))
  }, [load])

  useEffect(() => {
    if (!variations) return
    const isSettled = variations.every((v) => v.status === "generated" || v.status === "failed")
    if (isSettled) return
    const timer = setInterval(() => {
      aiVisualsApi.getVisuals(kind).then(setVariations).catch(() => {})
    }, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [variations, kind])

  async function retry() {
    setIsRetrying(true)
    try {
      await load()
    } catch (err) {
      setErrorMessage(getErrorMessage(err))
    } finally {
      setIsRetrying(false)
    }
  }

  return {
    variations,
    errorMessage,
    isRetrying,
    retry,
    canRetry: variations ? isRetryableFailureSet(variations) : false,
  }
}
