import { authenticatedRequest } from "@/lib/api/apiClient"

export type QuestionType = "text" | "single_select" | "multi_select" | "yes_no"

export interface ShowIf {
  question_id: string
  in_values: string[]
}

export interface Question {
  id: string
  number: number
  text: string
  type: QuestionType
  options: string[] | null
  required: boolean
  show_if: ShowIf | null
}

export interface QuestionSetResponse {
  questions: Question[]
  disclaimer_text: string
}

export type AnswerValue = string | string[]

export interface QuestionnaireResponseOut {
  id: string
  submitted_at: string
}

export interface QuestionnaireStatusResponse {
  completed: boolean
}

export function getQuestionSet(): Promise<QuestionSetResponse> {
  return authenticatedRequest<QuestionSetResponse>("/questionnaire", { method: "GET" })
}

export function getStatus(): Promise<QuestionnaireStatusResponse> {
  return authenticatedRequest<QuestionnaireStatusResponse>("/questionnaire/status", { method: "GET" })
}

export function submitResponse(
  answers: Record<string, AnswerValue>,
  disclaimerAccepted: boolean
): Promise<QuestionnaireResponseOut> {
  return authenticatedRequest<QuestionnaireResponseOut>("/questionnaire/responses", {
    method: "POST",
    body: { answers, disclaimer_accepted: disclaimerAccepted },
  })
}
