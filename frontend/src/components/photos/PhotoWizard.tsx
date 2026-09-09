"use client"

import { Loader2 } from "lucide-react"
import { motion } from "motion/react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { PhotoCaptureStep } from "@/components/photos/PhotoCaptureStep"
import { PhotoRequirementsStep } from "@/components/photos/PhotoRequirementsStep"
import { PhotoSetCompleteStep } from "@/components/photos/PhotoSetCompleteStep"
import { getNextOnboardingStep } from "@/lib/onboarding/nextStep"
import type { CaptureMethod, PhotoOut } from "@/lib/photos/photoApi"
import * as photoApi from "@/lib/photos/photoApi"
import { summarizePhotoValidationFailure } from "@/lib/photos/summarizeValidationFailure"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"
import { usePhotoStore } from "@/store/photoStore"

const REQUIREMENTS_STEP_ID = "requirements"

export function PhotoWizard() {
  const router = useRouter()
  const angles = usePhotoStore((state) => state.angles)
  const completed = usePhotoStore((state) => state.completed)
  const setAnglePhoto = usePhotoStore((state) => state.setAnglePhoto)
  const paymentStatus = usePaymentStore((state) => state.status)
  const analysisStatus = useAnalysisStore((state) => state.status)

  const [currentStepId, setCurrentStepId] = useState<string>(REQUIREMENTS_STEP_ID)
  const [isContinuing, setIsContinuing] = useState(false)
  /** When set, show capture for this angle even though the set is complete. */
  const [editingAngleId, setEditingAngleId] = useState<string | null>(null)

  if (!angles) {
    return (
      <div className="flex flex-1 items-center justify-center py-16">
        <Loader2 className="size-7 animate-spin text-primary/50" aria-label="Loading" />
      </div>
    )
  }

  const isRequirementsStep = currentStepId === REQUIREMENTS_STEP_ID
  const currentAngle = isRequirementsStep ? null : (angles.find((a) => a.angle === currentStepId) ?? null)

  function goToFirstIncompleteAngle() {
    const next = angles!.find((a) => a.photo?.validation_status !== "passed") ?? angles![0]
    setEditingAngleId(null)
    setCurrentStepId(next.angle)
  }

  function handleChangePhoto(angleId: string) {
    setEditingAngleId(angleId)
    setCurrentStepId(angleId)
  }

  function handleBackFromCapture() {
    if (editingAngleId || usePhotoStore.getState().completed) {
      // Return to the "All photos submitted" review — do not send them to
      // requirements (that branch is `isRequirementsStep && !editing`).
      setEditingAngleId(null)
      return
    }
    setCurrentStepId(REQUIREMENTS_STEP_ID)
  }

  async function handleSubmitAngle(blob: Blob, method: CaptureMethod): Promise<PhotoOut> {
    const wasCompleted = usePhotoStore.getState().completed
    const submittedAngleId = currentStepId
    const photo = await photoApi.uploadPhoto(currentStepId, method, blob)
    setAnglePhoto(currentStepId, photo)

    if (photo.validation_status === "passed") {
      toast.success(`${currentAngle?.label ?? "Photo"} accepted.`)

      if (editingAngleId === submittedAngleId) {
        setEditingAngleId(null)
        return photo
      }

      const next = angles!.find(
        (a) => a.angle !== currentStepId && a.photo?.validation_status !== "passed"
      )
      // Prefer the next incomplete after the current one in order.
      const idx = angles!.findIndex((a) => a.angle === currentStepId)
      const nextInOrder = angles!.slice(idx + 1).find((a) => a.photo?.validation_status !== "passed")
      const advanceTo = nextInOrder ?? next
      if (advanceTo) {
        setCurrentStepId(advanceTo.angle)
      }
    } else {
      toast.error(summarizePhotoValidationFailure(photo.checks))
    }

    if (!wasCompleted && usePhotoStore.getState().completed) {
      toast.success("All photos submitted!")
    }

    return photo
  }

  function handleContinue() {
    setIsContinuing(true)
    router.replace(
      getNextOnboardingStep({
        questionnaireCompleted: true,
        photosCompleted: true,
        paymentSucceeded: paymentStatus === "succeeded",
        analysisStatus: analysisStatus ?? "none",
      })
    )
  }

  if (isRequirementsStep && !editingAngleId) {
    return (
      <section className="grid min-h-full flex-1 lg:grid-cols-[0.8fr_1.2fr]">
        <aside className="relative hidden flex-col items-center justify-center gap-8 px-8 py-10 lg:flex">
          <motion.div
            className="absolute inset-[14%] rounded-full bg-primary/[0.07] blur-3xl"
            animate={{ scale: [1, 1.05, 1], opacity: [0.45, 0.8, 0.45] }}
            transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            initial={{ opacity: 0.7, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.35 }}
            className="relative"
          >
            <FacialScanVisual className="h-[min(56vh,400px)] w-auto" tone="onLight" />
          </motion.div>
        </aside>

        <div className="flex flex-col items-center justify-center px-5 py-8 sm:px-8 lg:pr-14 lg:pl-6">
          <div className="w-full max-w-3xl">
            <PhotoRequirementsStep onContinue={goToFirstIncompleteAngle} />
          </div>
        </div>
      </section>
    )
  }

  if (completed && !editingAngleId) {
    return (
      <section className="grid min-h-full flex-1 lg:grid-cols-[0.8fr_1.2fr]">
        <aside className="relative hidden flex-col items-center justify-center gap-8 px-8 py-10 lg:flex">
          <motion.div
            className="absolute inset-[14%] rounded-full bg-primary/[0.07] blur-3xl"
            animate={{ scale: [1, 1.05, 1], opacity: [0.45, 0.8, 0.45] }}
            transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            initial={{ opacity: 0.7, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.35 }}
            className="relative"
          >
            <FacialScanVisual className="h-[min(56vh,400px)] w-auto" tone="onLight" />
          </motion.div>
        </aside>

        <div className="flex flex-col items-center justify-center px-5 py-8 sm:px-8 lg:pr-14 lg:pl-6">
          <PhotoSetCompleteStep
            angles={angles}
            isContinuing={isContinuing}
            onContinue={handleContinue}
            onChangePhoto={handleChangePhoto}
          />
        </div>
      </section>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <PhotoCaptureStep
        angles={angles}
        currentAngleId={currentStepId === REQUIREMENTS_STEP_ID ? angles[0]!.angle : currentStepId}
        onSelectAngle={(angleId) => {
          if (completed || editingAngleId) {
            setEditingAngleId(angleId)
          }
          setCurrentStepId(angleId)
        }}
        onBackToRequirements={handleBackFromCapture}
        onSubmit={handleSubmitAngle}
        startFresh={editingAngleId !== null}
      />
    </div>
  )
}
