import { authenticatedRequest, authenticatedStreamRequest } from "@/lib/api/apiClient"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
}

export interface ChatHistory {
  messages: ChatMessage[]
  // Always computed fresh from the report's current sections -- shown only
  // when `messages` is empty (see chat_service.get_history's docstring).
  suggested_prompts: string[]
}

export function getHistory(): Promise<ChatHistory> {
  return authenticatedRequest<ChatHistory>("/chat/history", { method: "GET" })
}

/**
 * Streams the assistant's reply for a new message as plain-text chunks,
 * decoded incrementally as the server sends them. POST /chat/messages
 * responds `text/plain` (not JSON, see chat_service.stream_reply), so this
 * bypasses the JSON-parsing authenticatedRequest helpers entirely and reads
 * the raw Response body instead.
 */
export async function* streamMessage(content: string): AsyncGenerator<string> {
  const response = await authenticatedStreamRequest("/chat/messages", { content })
  const reader = response.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) return
    yield decoder.decode(value, { stream: true })
  }
}
