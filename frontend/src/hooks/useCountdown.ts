import { useEffect, useState } from "react"

function computeRemainingSeconds(targetTimestampMs: number | null): number {
  if (targetTimestampMs === null) return 0
  return Math.max(0, Math.ceil((targetTimestampMs - Date.now()) / 1000))
}

/**
 * Seconds remaining until an absolute timestamp, ticking once per second.
 *
 * Deliberately recomputed from `Date.now()` vs. the target on every tick,
 * rather than decremented -- a decrementing counter drifts (and can even
 * run past zero) when a backgrounded/throttled tab skips or delays
 * `setInterval` ticks, since browsers throttle timers in inactive tabs.
 * Recomputing from the absolute target self-corrects regardless of how
 * late a given tick actually fires.
 */
export function useCountdown(targetTimestampMs: number | null): number {
  const [trackedTarget, setTrackedTarget] = useState(targetTimestampMs)
  const [remaining, setRemaining] = useState(() => computeRemainingSeconds(targetTimestampMs))

  // React's documented pattern for "reset state when a prop changes":
  // adjust it directly during render rather than in an effect, so there's
  // no stale-value flash and no extra effect-triggered render pass.
  if (targetTimestampMs !== trackedTarget) {
    setTrackedTarget(targetTimestampMs)
    setRemaining(computeRemainingSeconds(targetTimestampMs))
  }

  useEffect(() => {
    if (targetTimestampMs === null) return

    // The effect's only job is subscribing to the ticking timer; the
    // initial/reset value is handled during render above.
    const interval = setInterval(() => {
      setRemaining(computeRemainingSeconds(targetTimestampMs))
    }, 1000)

    return () => clearInterval(interval)
  }, [targetTimestampMs])

  return remaining
}
