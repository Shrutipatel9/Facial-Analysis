"use client"

import {
  ArrowLeft,
  Camera,
  Check,
  ImageIcon,
  Loader2,
  RotateCcw,
  Upload,
  X,
} from "lucide-react"
import Image from "next/image"
import { useEffect, useRef, useState } from "react"

import { CameraCapture } from "@/components/photos/CameraCapture"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { CaptureMethod, PhotoAngleStatus, PhotoOut } from "@/lib/photos/photoApi"
import { summarizePhotoValidationFailure } from "@/lib/photos/summarizeValidationFailure"
import { cn } from "@/lib/utils"

const CAPTURE_TIPS = [
  "Look straight at the camera",
  "Maintain a neutral expression",
  "Remove hair and obstructions from the face",
  "Photo taken from an arm's length away",
  "Only one head should be visible in the image",
  "The head and neck are not cropped out",
  "Keep camera focused and not blurry",
  "Ensure consistent, even lighting",
  "Ensure a plain, clear background",
] as const

const POSE_GUIDE_SRC: Record<string, string> = {
  front: "/pose-guides/front.jpg",
  right_3q: "/pose-guides/right.jpg",
  left_3q: "/pose-guides/left.jpg",
}

type Mode = "choose" | "camera" | "preview" | "result"

interface PhotoCaptureStepProps {
  angles: PhotoAngleStatus[]
  currentAngleId: string
  onSelectAngle: (angleId: string) => void
  onBackToRequirements: () => void
  onSubmit: (blob: Blob, method: CaptureMethod) => Promise<PhotoOut>
}

export function PhotoCaptureStep({
  angles,
  currentAngleId,
  onSelectAngle,
  onBackToRequirements,
  onSubmit,
}: PhotoCaptureStepProps) {
  const angle = angles.find((a) => a.angle === currentAngleId) ?? angles[0]!
  const [mode, setMode] = useState<Mode>(angle.photo ? "result" : "choose")
  const [pendingBlob, setPendingBlob] = useState<Blob | null>(null)
  const [pendingMethod, setPendingMethod] = useState<CaptureMethod>("upload")
  /** Local blob previews keyed by angle — kept after submit so result screen can show the image. */
  const [previewByAngle, setPreviewByAngle] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const previewByAngleRef = useRef(previewByAngle)
  previewByAngleRef.current = previewByAngle
  const previewUrl = previewByAngle[currentAngleId] ?? null

  // Revoke all object URLs on unmount.
  useEffect(() => {
    return () => {
      for (const url of Object.values(previewByAngleRef.current)) {
        URL.revokeObjectURL(url)
      }
    }
  }, [])

  // Switch pose without remounting the whole layout — only reset the right pane.
  useEffect(() => {
    setPendingBlob(null)
    const current = angles.find((a) => a.angle === currentAngleId)
    setMode(current?.photo ? "result" : "choose")
    setIsSubmitting(false)
    // Only when the selected pose changes — not on every angles store update.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional
  }, [currentAngleId])

  function pickFile(blob: Blob, method: CaptureMethod) {
    setPendingBlob(blob)
    setPendingMethod(method)
    const nextUrl = URL.createObjectURL(blob)
    setPreviewByAngle((prev) => {
      const previous = prev[currentAngleId]
      if (previous) URL.revokeObjectURL(previous)
      return { ...prev, [currentAngleId]: nextUrl }
    })
    setMode("preview")
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ""
    if (file) pickFile(file, "upload")
  }

  function handleRetake() {
    setPendingBlob(null)
    setPreviewByAngle((prev) => {
      const previous = prev[currentAngleId]
      if (previous) URL.revokeObjectURL(previous)
      const next = { ...prev }
      delete next[currentAngleId]
      return next
    })
    setMode("choose")
  }

  async function handleUseThisPhoto() {
    if (!pendingBlob) return
    setIsSubmitting(true)
    try {
      await onSubmit(pendingBlob, pendingMethod)
      // Keep previewByAngle so the result screen still shows the submitted image.
      setPendingBlob(null)
      setMode("result")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="grid min-h-full flex-1 lg:grid-cols-[minmax(18rem,26rem)_minmax(0,1fr)]">
      {/* Left rail — grows with content; page scrolls only if it overflows */}
      <aside className="flex flex-col gap-4 border-border bg-card px-5 py-5 sm:px-6 lg:border-r lg:py-6">
        <button
          type="button"
          onClick={onBackToRequirements}
          className="inline-flex w-fit shrink-0 items-center gap-1.5 text-sm text-muted-foreground transition hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back
        </button>

        <div className="shrink-0 space-y-1.5">
          <h1 className="font-sans text-xl font-semibold tracking-tight text-balance sm:text-2xl">
            Upload Your Images
          </h1>
          <p className="text-xs leading-relaxed text-muted-foreground text-pretty sm:text-sm">
            You&apos;re almost done! Once we have your images, we can begin your facial analysis.
          </p>
        </div>

        <div className="shrink-0 space-y-2">
          <p className="text-[10px] font-medium tracking-[0.16em] text-muted-foreground uppercase">
            Poses required
          </p>
          <div className="flex justify-start gap-2">
            {angles.map((item) => {
              const selected = item.angle === angle.angle
              const passed = item.photo?.validation_status === "passed"
              return (
                <button
                  key={item.angle}
                  type="button"
                  onClick={() => onSelectAngle(item.angle)}
                  className={cn(
                    "relative w-[4.75rem] shrink-0 overflow-hidden rounded-lg border border-border transition sm:w-[5.25rem]",
                    !selected && "hover:border-primary/25"
                  )}
                >
                  <Image
                    src={POSE_GUIDE_SRC[item.angle] ?? POSE_GUIDE_SRC.front!}
                    alt={item.label}
                    width={84}
                    height={105}
                    className={cn(
                      "aspect-3/4 w-full object-cover transition",
                      !selected && "blur-[1px]"
                    )}
                  />
                  {!selected ? (
                    <span className="absolute inset-0 bg-black/45" aria-hidden />
                  ) : null}
                  {passed ? (
                    <span className="absolute top-1 right-1 z-10 flex size-4 items-center justify-center rounded-full bg-success text-success-foreground shadow-sm">
                      <Check className="size-2.5" strokeWidth={3} />
                    </span>
                  ) : null}
                  <span
                    className={cn(
                      "absolute inset-x-0 bottom-0 z-10 px-0.5 py-0.5 text-center text-[9px] font-medium leading-tight text-white",
                      selected ? "bg-black/50" : "bg-black/60"
                    )}
                  >
                    {item.label}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <p className="text-[10px] font-medium tracking-[0.16em] text-muted-foreground uppercase">
            Required
          </p>
          <ul className="rounded-xl border border-border bg-background/60 p-2">
            {CAPTURE_TIPS.map((tip, index) => (
              <li
                key={tip}
                className={cn(
                  "flex items-start gap-2.5 px-3 py-1.5 text-[11px] leading-snug sm:text-xs",
                  index < CAPTURE_TIPS.length - 1 && "border-b border-border"
                )}
              >
                <span className="mt-0.5 flex size-3.5 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
                  <Check className="size-2" strokeWidth={3} aria-hidden />
                </span>
                <span className="text-foreground/85">{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* Right workspace — no decorative wave background */}
      <div className="flex min-h-full flex-1 flex-col bg-[#eef1f3] px-5 py-6 sm:px-8 lg:px-10 lg:py-8">
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col">
          <div className="mb-6 space-y-1 text-center">
            <h2 className="font-sans text-2xl font-semibold tracking-tight sm:text-3xl">{angle.label}</h2>
            <p className="text-sm text-muted-foreground">{angle.instruction}</p>
          </div>

          <div className="flex flex-1 flex-col justify-center">
            {mode === "choose" ? (
              <div className="mx-auto w-full max-w-xl space-y-4 rounded-3xl border border-white/70 bg-white/70 p-6 shadow-sm backdrop-blur-sm sm:p-8">
                <div className="flex flex-col items-center gap-3 text-center">
                  <span className="flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md shadow-primary/20">
                    <Upload className="size-6" />
                  </span>
                  <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    .JPG · .PNG · .HEIC
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Drag and drop, or choose how to add this pose
                  </p>
                </div>

                <div
                  className="rounded-2xl border border-dashed border-primary/25 bg-background/50 px-4 py-8 text-center transition hover:border-primary/40"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault()
                    const file = e.dataTransfer.files?.[0]
                    if (file?.type.startsWith("image/")) pickFile(file, "upload")
                  }}
                >
                  <p className="text-sm text-muted-foreground">Drop an image here</p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 rounded-full border-border"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <ImageIcon className="size-4" />
                    Upload from gallery
                  </Button>
                  <Button
                    type="button"
                    className="h-11 rounded-full"
                    onClick={() => setMode("camera")}
                  >
                    <Camera className="size-4" />
                    Use camera
                  </Button>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/heic,image/heif"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            ) : null}

            {mode === "camera" ? (
              <div className="mx-auto w-full max-w-xl rounded-3xl border border-border bg-card p-4 sm:p-6">
                <CameraCapture
                  angleLabel={angle.label}
                  onCapture={(blob) => pickFile(blob, "camera")}
                  onCancel={() => setMode("choose")}
                />
              </div>
            ) : null}

            {mode === "preview" && previewUrl ? (
              <div className="mx-auto w-full max-w-xl space-y-4 rounded-3xl border border-border bg-card p-4 sm:p-6">
                {/* eslint-disable-next-line @next/next/no-img-element -- local blob URL */}
                <img
                  src={previewUrl}
                  alt={`${angle.label} preview`}
                  className="mx-auto max-h-[min(55vh,28rem)] w-auto rounded-2xl object-contain"
                />
                <div className="flex items-center justify-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    className="rounded-full"
                    onClick={handleRetake}
                    disabled={isSubmitting}
                  >
                    <RotateCcw className="size-4" />
                    Retake
                  </Button>
                  <Button
                    type="button"
                    className="rounded-full"
                    onClick={handleUseThisPhoto}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : null}
                    Use this photo
                  </Button>
                </div>
              </div>
            ) : null}

            {mode === "result" && angle.photo ? (
              <div className="mx-auto w-full max-w-xl space-y-4 rounded-3xl border border-border bg-card p-5 sm:p-6">
                {previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element -- local blob URL
                  <img
                    src={previewUrl}
                    alt={`${angle.label} submitted`}
                    className="mx-auto max-h-[min(45vh,22rem)] w-auto rounded-2xl object-contain"
                  />
                ) : null}

                <div
                  className={cn(
                    "flex items-center justify-between rounded-2xl border px-4 py-3.5",
                    angle.photo.validation_status === "passed"
                      ? "border-success/30 bg-success/10"
                      : "border-destructive/25 bg-destructive/[0.05]"
                  )}
                >
                  <span className="text-sm font-medium">
                    {angle.photo.validation_status === "passed"
                      ? "Photo accepted"
                      : "Try another photo"}
                  </span>
                  <Badge variant={angle.photo.validation_status === "passed" ? "default" : "destructive"}>
                    {angle.photo.validation_status}
                  </Badge>
                </div>

                {angle.photo.validation_status === "failed" ? (
                  <div className="flex items-start gap-2.5 rounded-xl border border-destructive/15 bg-destructive/[0.03] px-3.5 py-2.5 text-sm text-destructive">
                    <X className="mt-0.5 size-3.5 shrink-0" strokeWidth={3} />
                    <span>{summarizePhotoValidationFailure(angle.photo.checks)}</span>
                  </div>
                ) : null}

                <div className="flex justify-center">
                  <Button type="button" variant="outline" className="rounded-full" onClick={handleRetake}>
                    <RotateCcw className="size-4" />
                    {angle.photo.validation_status === "passed" ? "Retake this photo" : "Try again"}
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
