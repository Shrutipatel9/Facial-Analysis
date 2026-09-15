"use client"

import { Bot, User } from "lucide-react"

import { renderMarkdownLite } from "./markdownLite"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/lib/chat/chatApi"

interface ChatMessageListProps {
  messages: ChatMessage[]
  /** The in-flight assistant reply's text so far, or null when nothing is streaming. */
  streamingReply: string | null
}

export function ChatMessageList({ messages, streamingReply }: ChatMessageListProps) {
  return (
    <div className="flex flex-col gap-6">
      {messages.map((message) => (
        <ChatBubble key={message.id} role={message.role} content={message.content} />
      ))}
      {streamingReply !== null ? <ChatBubble role="assistant" content={streamingReply} isStreaming /> : null}
    </div>
  )
}

function ChatBubble({
  role,
  content,
  isStreaming,
}: {
  role: "user" | "assistant"
  content: string
  isStreaming?: boolean
}) {
  const isUser = role === "user"

  if (isUser) {
    return (
      <div className="flex items-end justify-end gap-2.5">
        <div className="max-w-[min(48rem,92%)] rounded-full bg-primary px-5 py-2.5 text-sm leading-relaxed text-primary-foreground">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
        <span className="mb-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground">
          <User className="size-4" aria-hidden />
        </span>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        {content === "" && isStreaming ? (
          <span
            className="size-3.5 animate-spin rounded-full border-2 border-primary/30 border-t-primary"
            aria-label="Assistant is typing"
          />
        ) : (
          <Bot className="size-4" aria-hidden />
        )}
      </span>
      <div className={cn("max-w-[min(56rem,94%)] text-sm leading-relaxed text-foreground")}>
        {content === "" && isStreaming ? (
          <span className="text-muted-foreground">Thinking…</span>
        ) : (
          renderMarkdownLite(content)
        )}
      </div>
    </div>
  )
}
