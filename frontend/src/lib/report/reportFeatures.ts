import {
  ChevronDown,
  CircleDot,
  Droplet,
  Ear,
  Eye,
  Minus,
  MoveVertical,
  Scissors,
  Smile,
  Square,
  Wind,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

// Fixed, verbatim order from FR-009/BR-008 -- mirrors
// Backend/app/services/facial_measurement_service.py's ANALYSIS_FEATURES.
export const FEATURE_ORDER = [
  "hair",
  "eyebrows",
  "eyes",
  "nose",
  "cheeks",
  "jaw",
  "lips",
  "chin",
  "skin",
  "neck",
  "ears",
] as const

export const FEATURE_LABELS: Record<string, string> = {
  hair: "Hair",
  eyebrows: "Eyebrows",
  eyes: "Eyes",
  nose: "Nose",
  cheeks: "Cheeks",
  jaw: "Jaw",
  lips: "Lips",
  chin: "Chin",
  skin: "Skin",
  neck: "Neck",
  ears: "Ears",
}

// One icon per feature, from a single library (Meridian §1.4's rule),
// never decorative -- always the same feature/icon pairing.
export const FEATURE_ICONS: Record<string, LucideIcon> = {
  hair: Scissors,
  eyebrows: Minus,
  eyes: Eye,
  nose: Wind,
  cheeks: CircleDot,
  jaw: Square,
  lips: Smile,
  chin: ChevronDown,
  skin: Droplet,
  neck: MoveVertical,
  ears: Ear,
}

export function featureAnchorId(feature: string): string {
  return `feature-${feature}`
}

export function assessmentAnchorId(assessment: string): string {
  return `assessment-${assessment}`
}
