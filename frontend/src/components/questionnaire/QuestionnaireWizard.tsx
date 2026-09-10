"use client"

import { ArrowRight, Loader2 } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { DisclaimerStep } from "@/components/questionnaire/DisclaimerStep"
import { QuestionStep } from "@/components/questionnaire/QuestionStep"
import { Button } from "@/components/ui/button"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { getNextOnboardingStep, isPhotosIdentityOk } from "@/lib/onboarding/nextStep"
import { isVisible } from "@/lib/questionnaire/isVisible"
import * as questionnaireApi from "@/lib/questionnaire/questionnaireApi"
import type { AnswerValue, Question } from "@/lib/questionnaire/questionnaireApi"
import { answerSchemaFor, disclaimerSchema } from "@/lib/validation"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"
import { usePhotoStore } from "@/store/photoStore"
import { useQuestionnaireStore } from "@/store/questionnaireStore"

const DISCLAIMER_STEP_ID = "disclaimer"

export function QuestionnaireWizard() {
  const router = useRouter()
  const [questions, setQuestions] = useState<Question[] | null>(null)
  const [disclaimerText, setDisclaimerText] = useState("")
  const [loadError, setLoadError] = useState<string | null>(null)
  const [stepError, setStepError] = useState<string | undefined>(undefined)
  const [followUpError, setFollowUpError] = useState<string | undefined>(undefined)
  const [disclaimerError, setDisclaimerError] = useState<string | undefined>(undefined)
  const [isSubmitting, setIsSubmitting] = useState(false)
  /** Separate intro screen before Q1 — only dismissed by Continue. */
  const [hasStarted, setHasStarted] = useState(false)

  const answers = useQuestionnaireStore((state) => state.answers)
  const currentQuestionId = useQuestionnaireStore((state) => state.currentQuestionId)
  const disclaimerAccepted = useQuestionnaireStore((state) => state.disclaimerAccepted)
  const setAnswer = useQuestionnaireStore((state) => state.setAnswer)
  const goTo = useQuestionnaireStore((state) => state.goTo)
  const setDisclaimerAccepted = useQuestionnaireStore((state) => state.setDisclaimerAccepted)
  const setCompleted = useQuestionnaireStore((state) => state.setCompleted)
  const reset = useQuestionnaireStore((state) => state.reset)
  const photosCompleted = usePhotoStore((state) => state.completed)
  const photosIdentityCheck = usePhotoStore((state) => state.identityCheck)
  const paymentStatus = usePaymentStore((state) => state.status)
  const analysisStatus = useAnalysisStore((state) => state.status)

  useEffect(() => {
    questionnaireApi
      .getQuestionSet()
      .then((res) => {
        setQuestions(res.questions)
        setDisclaimerText(res.disclaimer_text)
      })
      .catch((err) => setLoadError(getErrorMessage(err)))
  }, [])

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="text-center text-sm font-medium text-destructive">{loadError}</p>
      </div>
    )
  }

  if (!questions) {
    return (
      <div className="flex flex-1 items-center justify-center py-16">
        <Loader2 className="size-7 animate-spin text-primary/50" aria-label="Loading" />
      </div>
    )
  }

  // Once submission starts, render a dedicated loading state for the rest of
  // this component's lifetime instead of the wizard body. `handleSubmit`
  // calls `reset()` (clears answers/currentQuestionId) before `router.replace`
  // resolves -- client-side navigation doesn't unmount this component
  // synchronously, so without this guard the wizard would briefly re-render
  // showing Q1 (currentQuestionId falls back to stepIds[0]) before the route
  // actually changes. This makes that flicker structurally impossible.
  if (isSubmitting) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16 text-center">
        <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
        <p className="text-base text-muted-foreground">Submitting your answers…</p>
      </div>
    )
  }

  const topLevelQuestions = questions.filter((q) => !q.id.endsWith("_details"))
  const visibleSteps = topLevelQuestions.filter((q) => isVisible(q, answers))
  const stepIds = [...visibleSteps.map((q) => q.id), DISCLAIMER_STEP_ID]
  const currentId = currentQuestionId && stepIds.includes(currentQuestionId) ? currentQuestionId : stepIds[0]
  const currentIndex = stepIds.indexOf(currentId)
  const isDisclaimerStep = currentId === DISCLAIMER_STEP_ID
  const currentQuestion = isDisclaimerStep ? null : (questions.find((q) => q.id === currentId) ?? null)
  const followUp =
    currentQuestion && (currentQuestion.id === "q9" || currentQuestion.id === "q11")
      ? questions.find((q) => q.show_if?.question_id === currentQuestion.id)
      : undefined
  const followUpVisible = followUp ? isVisible(followUp, answers) : false
  const progressNumber = isDisclaimerStep ? 23 : (currentQuestion?.number ?? 1)
  const showIntro = !hasStarted

  function handleBack() {
    setStepError(undefined)
    setFollowUpError(undefined)
    const prevIndex = Math.max(currentIndex - 1, 0)
    goTo(stepIds[prevIndex])
  }

  function handleNext() {
    if (!currentQuestion) return

    const parsed = answerSchemaFor(currentQuestion).safeParse(answers[currentQuestion.id])
    if (!parsed.success) {
      setStepError(parsed.error.issues[0]?.message)
      return
    }

    const updatedAnswers: Record<string, AnswerValue> = {
      ...answers,
      [currentQuestion.id]: parsed.data as AnswerValue,
    }
    setAnswer(currentQuestion.id, parsed.data as AnswerValue)

    if (followUp && isVisible(followUp, updatedAnswers)) {
      const followUpParsed = answerSchemaFor(followUp).safeParse(answers[followUp.id])
      if (!followUpParsed.success) {
        setFollowUpError(followUpParsed.error.issues[0]?.message)
        return
      }
      updatedAnswers[followUp.id] = followUpParsed.data as AnswerValue
      setAnswer(followUp.id, followUpParsed.data as AnswerValue)
    }

    setStepError(undefined)
    setFollowUpError(undefined)

    const updatedVisibleSteps = topLevelQuestions.filter((q) => isVisible(q, updatedAnswers))
    const updatedStepIds = [...updatedVisibleSteps.map((q) => q.id), DISCLAIMER_STEP_ID]
    const idx = updatedStepIds.indexOf(currentQuestion.id)
    goTo(updatedStepIds[idx + 1] ?? DISCLAIMER_STEP_ID)
  }

  async function handleSubmit() {
    const parsed = disclaimerSchema.safeParse({ disclaimerAccepted })
    if (!parsed.success) {
      setDisclaimerError(parsed.error.issues[0]?.message)
      return
    }

    setIsSubmitting(true)
    try {
      await questionnaireApi.submitResponse(answers, true)
      setCompleted(true)
      toast.success("Questionnaire submitted.")
      reset()
      // Navigate straight to the actual next step -- never relay through
      // /dashboard. By this point the photo/analysis guards have almost
      // certainly already resolved their own status fetches in the
      // background (they were enabled the moment this guard cleared, back
      // when this page first mounted), so routing through /dashboard would
      // render its real "you're all set" content for one frame before
      // useOnboardingEntryGuard yanks it away again. See
      // lib/onboarding/nextStep.ts.
      router.replace(
        getNextOnboardingStep({
          questionnaireCompleted: true,
          photosCompleted: photosCompleted ?? false,
          photosIdentityConsistent: isPhotosIdentityOk(photosCompleted, photosIdentityCheck),
          paymentSucceeded: paymentStatus === "succeeded",
          analysisStatus: analysisStatus ?? "none",
        })
      )
    } catch (err) {
      toast.error(getErrorMessage(err))
      setIsSubmitting(false)
    }
  }

  return (
    <section className="grid min-h-full flex-1 lg:grid-cols-[0.8fr_1.2fr]">
      <aside className="relative hidden flex-col items-center justify-center gap-8 px-8 py-10 lg:flex">
        <motion.div
          className="absolute inset-[14%] rounded-full bg-primary/[0.07] blur-3xl"
          animate={{ scale: [1, 1.05, 1], opacity: [0.45, 0.8, 0.45] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        />

        <motion.div
          key={showIntro ? "intro" : currentId}
          initial={{ opacity: 0.7, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35 }}
          className="relative"
        >
          <FacialScanVisual className="h-[min(56vh,400px)] w-auto" tone="onLight" />
        </motion.div>

        <div className="relative space-y-2 text-center">
          {!showIntro ? (
            <>
              <p className="text-[11px] font-medium tracking-[0.22em] text-primary/55 uppercase">
                {isDisclaimerStep ? "Final step" : "Building your profile"}
              </p>
              <p className="font-heading text-3xl font-semibold tabular-nums tracking-tight text-primary">
                {String(progressNumber).padStart(2, "0")}
                <span className="text-primary/35"> / 23</span>
              </p>
            </>
          ) : null}
        </div>
      </aside>

      <div className="flex flex-col items-center justify-center px-5 py-8 sm:px-8 lg:pr-14 lg:pl-6">
        <div className="flex w-full max-w-3xl flex-col items-stretch gap-5">
          <AnimatePresence mode="wait">
            {showIntro ? (
              <motion.div
                key="intro"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className="w-full space-y-5 rounded-2xl border border-border bg-card p-6 sm:p-8"
              >
                <div className="space-y-3">
                  <p className="text-[11px] font-medium tracking-[0.18em] text-primary/70 uppercase">
                    Onboarding Questions
                  </p>
                  <h2 className="font-heading text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
                    A few questions before your analysis
                  </h2>
                  <p className="text-[15px] leading-relaxed text-muted-foreground text-pretty">
                    We need you to answer a short questionnaire so we can tailor your facial
                    analysis. It takes about five minutes, then you can continue to photo capture
                    and your report.
                  </p>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key={currentId}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className="w-full rounded-2xl border border-border bg-card p-6 sm:p-7"
              >
                {isDisclaimerStep ? (
                  <DisclaimerStep
                    disclaimerText={disclaimerText}
                    accepted={disclaimerAccepted}
                    onAcceptedChange={setDisclaimerAccepted}
                    error={disclaimerError}
                  />
                ) : currentQuestion ? (
                  <QuestionStep
                    question={currentQuestion}
                    value={answers[currentQuestion.id]}
                    onChange={(value) => setAnswer(currentQuestion.id, value)}
                    error={stepError}
                    followUp={followUpVisible ? followUp : undefined}
                    followUpValue={followUp ? answers[followUp.id] : undefined}
                    onFollowUpChange={followUp ? (value) => setAnswer(followUp.id, value) : undefined}
                    followUpError={followUpError}
                  />
                ) : null}
              </motion.div>
            )}
          </AnimatePresence>

          {showIntro ? (
            <div className="flex w-full justify-end">
              <Button
                type="button"
                className="h-11 w-40 shrink-0 rounded-full sm:w-44"
                onClick={() => setHasStarted(true)}
              >
                Continue
                <ArrowRight />
              </Button>
            </div>
          ) : (
            <div className="flex w-full items-center justify-between gap-4">
              <Button
                type="button"
                variant="outline"
                className="h-11 w-28 shrink-0 rounded-full border-border sm:w-32"
                onClick={handleBack}
                disabled={currentIndex === 0}
              >
                Back
              </Button>
              {isDisclaimerStep ? (
                <Button
                  type="button"
                  className="h-11 w-36 shrink-0 rounded-full sm:w-40"
                  disabled={!disclaimerAccepted}
                  onClick={handleSubmit}
                >
                  Submit
                </Button>
              ) : (
                <Button
                  type="button"
                  className="h-11 w-36 shrink-0 rounded-full sm:w-40"
                  onClick={handleNext}
                >
                  Next
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
