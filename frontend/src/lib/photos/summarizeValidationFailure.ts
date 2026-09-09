import type { CheckResult } from "@/lib/photos/photoApi"

/**
 * Collapse the six backend check results into one actionable message.
 * Cascading "Skipped:" reasons are ignored; when several real checks fail,
 * prefer a single clear instruction over a technical checklist.
 */
export function summarizePhotoValidationFailure(checks: CheckResult[]): string {
  const primary = checks.filter(
    (check) => !check.passed && check.reason && !check.reason.startsWith("Skipped:")
  )

  if (primary.length === 0) {
    return "This photo didn’t pass validation. Please try again with a clearer photo of your face."
  }

  const failed = new Map(primary.map((check) => [check.check, check]))

  if (failed.has("file_readable")) {
    return "We couldn’t read this file as an image. Please upload a JPG or PNG photo."
  }

  const face = failed.get("face_count")
  if (face) {
    const multipleFaces = (face.reason ?? "").toLowerCase().includes("more than one")
    if (multipleFaces) {
      return "More than one face was detected. Please upload a photo with only your face visible."
    }
    // e.g. too small + no face → one message, not both technical reasons
    if (primary.length > 1) {
      return "No face detected. Please upload a clear, properly sized photo of your face."
    }
    return "No face detected. Please upload a clear photo of your face."
  }

  // A pose mismatch (e.g. a front-facing photo uploaded for a 3/4 angle
  // slot) is its own distinct, actionable issue -- surface it clearly even
  // when combined with other failures, same priority as face_count above.
  const pose = failed.get("pose_match")
  if (pose) {
    return pose.reason ?? "This photo doesn't match the angle for this step. Upload a photo of the correct pose."
  }

  if (primary.length === 1) {
    return friendlySingleReason(primary[0]!)
  }

  return "This photo doesn’t meet our quality requirements. Please use a clear, well-lit photo of your face that meets the size and framing guidelines."
}

function friendlySingleReason(check: CheckResult): string {
  switch (check.check) {
    case "resolution":
      return "This image is too small. Please upload a higher-resolution photo (at least 640px on the shortest side)."
    case "brightness":
      return check.reason ?? "Lighting looks uneven. Please retake with even, natural light."
    case "frame_proportion":
      return check.reason ?? "Adjust how close you are to the camera so your face fills the frame properly."
    case "occlusion":
      return check.reason ?? "Your face may be partially covered. Remove hats, glasses, or hair from the face."
    default:
      return check.reason ?? "This photo didn’t pass validation. Please try again."
  }
}
