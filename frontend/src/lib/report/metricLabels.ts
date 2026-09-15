// Mirrors Backend/app/services/report_pdf_service.py's
// _METRIC_LABEL_OVERRIDES / _humanize_metric_key -- same humanization rule
// (snake_case -> Title Case, "_px" suffix -> "(px)") kept in sync on both
// sides so the PDF and the interactive report show identical metric
// labels for the same raw measurement.metrics keys.
const METRIC_LABEL_OVERRIDES: Record<string, string> = {
  mean_r: "Mean Red",
  mean_g: "Mean Green",
  mean_b: "Mean Blue",
}

export function humanizeMetricKey(key: string): string {
  if (key in METRIC_LABEL_OVERRIDES) return METRIC_LABEL_OVERRIDES[key]
  const title = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  if (key.endsWith("_px")) return `${title(key.slice(0, -"_px".length))} (px)`
  return title(key)
}

/** `1.3333` -> "1.33", `120` -> "120" -- matches the PDF's `f"{value:g}"`
 * (trims trailing zeros, no fixed decimal count) closely enough for
 * display without pulling in a formatting library. */
export function formatMetricValue(value: number): string {
  if (Number.isInteger(value)) return String(value)
  return value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "")
}
