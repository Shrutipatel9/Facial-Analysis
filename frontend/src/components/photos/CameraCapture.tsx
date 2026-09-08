"use client"

import { Camera } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface CameraCaptureProps {
  angleLabel: string
  onCapture: (blob: Blob) => void
  onCancel: () => void
}

function cameraErrorMessage(err: unknown): string {
  if (typeof window !== "undefined" && !window.isSecureContext) {
    return "Camera needs a secure context (localhost or HTTPS). Open the app via localhost, or upload from gallery."
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    return "This browser does not support camera capture. Upload from gallery instead."
  }
  if (err instanceof DOMException) {
    switch (err.name) {
      case "NotAllowedError":
      case "PermissionDeniedError":
        return "Camera permission was denied. Allow camera access for this site in your browser settings, then try again — or upload from gallery."
      case "NotFoundError":
      case "DevicesNotFoundError":
        return "No camera was found on this device. Upload from gallery instead."
      case "NotReadableError":
      case "TrackStartError":
        return "Camera is busy (another app may be using it). Close other camera apps and try again, or upload from gallery."
      case "OverconstrainedError":
        return "No camera matched the requested settings. Try again, or upload from gallery."
      default:
        return `Camera unavailable (${err.name}). Try uploading from gallery instead.`
    }
  }
  return "Camera access failed. Try uploading from gallery instead."
}

/**
 * Live in-browser camera capture. Tries an ideal user-facing stream first,
 * then falls back to any video device — many “denied” failures were actually
 * OverconstrainedError from strict facingMode on desktops without a labeled
 * front camera.
 */
export function CameraCapture({ angleLabel, onCapture, onCancel }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function start() {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        if (!cancelled) setError(cameraErrorMessage(null))
        return
      }

      try {
        let stream: MediaStream
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: { ideal: "user" },
              width: { ideal: 1280 },
              height: { ideal: 720 },
            },
            audio: false,
          })
        } catch (firstErr) {
          // Desktops often reject facingMode constraints; any camera is fine.
          if (
            firstErr instanceof DOMException &&
            (firstErr.name === "OverconstrainedError" || firstErr.name === "NotFoundError")
          ) {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
          } else {
            throw firstErr
          }
        }

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        streamRef.current = stream
        const video = videoRef.current
        if (video) {
          video.srcObject = stream
          await video.play().catch(() => {
            /* autoplay can reject if muted isn't applied yet — video is muted */
          })
        }
        setIsReady(true)
      } catch (err) {
        if (!cancelled) setError(cameraErrorMessage(err))
      }
    }

    void start()

    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }, [])

  function handleShutter() {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(blob)
      },
      "image/jpeg",
      0.92
    )
  }

  if (error) {
    return (
      <div className="space-y-4 rounded-2xl border border-destructive/20 bg-destructive/[0.04] p-6 text-center">
        <p className="text-sm font-medium text-destructive text-pretty">{error}</p>
        <Button type="button" variant="outline" onClick={onCancel}>
          Back to upload options
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="relative aspect-4/3 w-full overflow-hidden rounded-2xl bg-black">
        <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div
            className={cn(
              "h-[70%] w-[46%] rounded-[50%] border-2 border-dashed border-white/60 transition-transform",
              angleLabel === "Left Side" && "-translate-x-[6%] -rotate-6",
              angleLabel === "Right Side" && "translate-x-[6%] rotate-6"
            )}
          />
        </div>
        {!isReady ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 text-sm text-white">
            Starting camera…
          </div>
        ) : null}
      </div>
      <canvas ref={canvasRef} className="hidden" />
      <div className="flex items-center justify-center gap-3">
        <Button type="button" variant="outline" className="rounded-full" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" className="gap-2 rounded-full" onClick={handleShutter} disabled={!isReady}>
          <Camera className="size-4" />
          Capture
        </Button>
      </div>
    </div>
  )
}
