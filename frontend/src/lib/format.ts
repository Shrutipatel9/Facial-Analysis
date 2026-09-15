export function formatCurrencyCents(cents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(cents / 100)
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })
}

/** "2m 14s" / "48s" style -- for the Dashboard's real "Analysis Time" stat
 * (report_full.analysis_duration_seconds). Caller omits the stat tile
 * entirely when the value is null, so this never needs to format "N/A". */
export function formatDuration(seconds: number): string {
  const totalSeconds = Math.round(seconds)
  const minutes = Math.floor(totalSeconds / 60)
  const remainingSeconds = totalSeconds % 60
  if (minutes === 0) return `${remainingSeconds}s`
  return `${minutes}m ${remainingSeconds}s`
}
