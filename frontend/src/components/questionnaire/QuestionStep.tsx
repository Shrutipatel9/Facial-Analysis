"use client"

import { Check } from "lucide-react"

import { Checkbox } from "@/components/ui/checkbox"
import { Textarea } from "@/components/ui/textarea"
import type { AnswerValue, Question } from "@/lib/questionnaire/questionnaireApi"
import { cn } from "@/lib/utils"

interface QuestionStepProps {
  question: Question
  value: AnswerValue | undefined
  onChange: (value: AnswerValue) => void
  error?: string
  followUp?: Question
  followUpValue?: AnswerValue | undefined
  onFollowUpChange?: (value: AnswerValue) => void
  followUpError?: string
}

export function QuestionStep({
  question,
  value,
  onChange,
  error,
  followUp,
  followUpValue,
  onFollowUpChange,
  followUpError,
}: QuestionStepProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <h2 className="font-sans text-xl font-semibold tracking-tight text-balance sm:text-2xl">
          {question.text}
        </h2>
        <QuestionInput question={question} value={value} onChange={onChange} />
        {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}
      </div>

      {followUp && onFollowUpChange ? (
        <div className="space-y-2.5 rounded-2xl border border-primary/10 bg-primary/[0.03] p-4">
          <p className="text-sm font-medium">{followUp.text}</p>
          <Textarea
            value={typeof followUpValue === "string" ? followUpValue : ""}
            onChange={(e) => onFollowUpChange(e.target.value)}
            placeholder="Optional details"
            className="min-h-24 border-primary/10 bg-card"
          />
          {followUpError ? <p className="text-sm font-medium text-destructive">{followUpError}</p> : null}
        </div>
      ) : null}
    </div>
  )
}

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: Question
  value: AnswerValue | undefined
  onChange: (value: AnswerValue) => void
}) {
  if (question.type === "multi_select") {
    const selected = Array.isArray(value) ? value : []
    return (
      <div className="grid gap-2.5">
        {question.options?.map((option) => {
          const isOn = selected.includes(option)
          return (
            <button
              key={option}
              type="button"
              onClick={() =>
                onChange(isOn ? selected.filter((o) => o !== option) : [...selected, option])
              }
              className={cn(
                "flex w-full cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3.5 text-left text-base transition",
                isOn
                  ? "border-primary/35 bg-primary/[0.08] shadow-sm shadow-primary/10"
                  : "border-primary/10 bg-card hover:border-primary/20 hover:bg-primary/[0.03]"
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md border transition",
                  isOn ? "border-primary bg-primary text-primary-foreground" : "border-primary/25"
                )}
              >
                {isOn ? <Check className="size-3" strokeWidth={3} /> : null}
              </span>
              <span className="leading-snug">{option}</span>
              <Checkbox className="sr-only" checked={isOn} tabIndex={-1} aria-hidden />
            </button>
          )
        })}
      </div>
    )
  }

  if (question.type === "single_select" || question.type === "yes_no") {
    const current = typeof value === "string" ? value : ""
    return (
      <div className="grid gap-2.5">
        {question.options?.map((option) => {
          const isOn = current === option
          return (
            <button
              key={option}
              type="button"
              onClick={() => onChange(option)}
              className={cn(
                "flex w-full cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3.5 text-left text-base transition",
                isOn
                  ? "border-primary/35 bg-primary/[0.08] shadow-sm shadow-primary/10"
                  : "border-primary/10 bg-card hover:border-primary/20 hover:bg-primary/[0.03]"
              )}
            >
              <span
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-full border transition",
                  isOn ? "border-primary bg-primary" : "border-primary/25"
                )}
              >
                {isOn ? <span className="size-2 rounded-full bg-primary-foreground" /> : null}
              </span>
              <span className="leading-snug font-medium">{option}</span>
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <Textarea
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      autoFocus
      className="min-h-32 rounded-2xl border-primary/12 bg-card px-4 py-3.5 text-base shadow-sm focus-visible:border-primary/30"
      placeholder="Type your answer…"
    />
  )
}
