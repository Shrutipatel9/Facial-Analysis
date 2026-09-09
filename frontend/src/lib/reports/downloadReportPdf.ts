import { downloadPdf } from "@/lib/reports/reportApi"

/** Fetches the report PDF and triggers a browser save via a temporary
 * object-URL anchor. Shared by ReportScreen (in-report download button)
 * and the dashboard's report card so the filename convention (matching
 * the backend's Content-Disposition -- see reports.py's get_report_pdf)
 * only lives in one place. */
export async function downloadReportPdf(reportId: string, createdAt: string): Promise<void> {
  const blob = await downloadPdf(reportId)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = `facial_report_${createdAt.slice(0, 10)}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
