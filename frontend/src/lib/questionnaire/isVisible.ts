import type { AnswerValue, Question } from "@/lib/questionnaire/questionnaireApi"

/** Tiny client-side port of Backend/app/services/questionnaire_service.py's
 * is_visible -- deliberately duplicated rather than shared over the wire;
 * it's ~5 lines and this is the entire "branching engine" for a fixed,
 * 23-question set (Q19, and the Q9/Q11 follow-ups). The backend is still
 * the authority -- this only drives which step the wizard shows next. */
export function isVisible(question: Question, answers: Record<string, AnswerValue>): boolean {
  if (!question.show_if) return true
  const answer = answers[question.show_if.question_id]
  return typeof answer === "string" && question.show_if.in_values.includes(answer)
}
