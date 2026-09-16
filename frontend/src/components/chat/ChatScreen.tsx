"use client"

import { AlertCircle, Bot, Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { ChatInput } from "./ChatInput"
import { ChatMessageList } from "./ChatMessageList"
import { SuggestedPrompts } from "./SuggestedPrompts"
import {
  workspaceShellClassName,
  workspaceUnifiedPanelClassName,
} from "@/components/layout/workspaceChrome"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as chatApi from "@/lib/chat/chatApi"
import type { ChatMessage } from "@/lib/chat/chatApi"
import { cn } from "@/lib/utils"
import { useAnalysisStore } from "@/store/analysisStore"

const STREAM_FALLBACK_MESSAGE = "Sorry, something went wrong generating a response. Please try asking again."

/**
 * Chat Assistant: muted outer frame + one white rounded panel (MyFace screenshot).
 */
export function ChatScreen() {
  const status = useAnalysisStore((state) => state.status)

  if (status !== "completed") {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Chat not available yet</h1>
        <p className="max-w-md text-base leading-relaxed text-muted-foreground">
          Finish your facial analysis first to unlock the AI Beauty Assistant.
        </p>
      </div>
    )
  }

  return <ChatConversation />
}

function ChatConversation() {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null)
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [streamingReply, setStreamingReply] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatApi
      .getHistory()
      .then((history) => {
        setMessages(history.messages)
        setSuggestedPrompts(history.suggested_prompts)
      })
      .catch((err) => setLoadError(getErrorMessage(err)))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, streamingReply])

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    }
    setMessages((current) => [...(current ?? []), userMessage])
    setIsSending(true)
    setStreamingReply("")

    let accumulated = ""
    try {
      for await (const chunk of chatApi.streamMessage(content)) {
        accumulated += chunk
        setStreamingReply(accumulated)
      }
    } catch (err) {
      accumulated = getErrorMessage(err) || STREAM_FALLBACK_MESSAGE
    } finally {
      setMessages((current) => [
        ...(current ?? []),
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: accumulated || STREAM_FALLBACK_MESSAGE,
          created_at: new Date().toISOString(),
        },
      ])
      setStreamingReply(null)
      setIsSending(false)
    }
  }

  if (loadError) {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <p className="max-w-md text-base leading-relaxed text-muted-foreground">{loadError}</p>
      </div>
    )
  }

  if (messages === null) {
    return (
      <div className="flex h-full min-h-0 flex-1 items-center justify-center py-16">
        <Loader2 className="size-6 animate-spin text-primary/60" aria-label="Loading" />
      </div>
    )
  }

  const hasMessages = messages.length > 0

  return (
    <div className={workspaceShellClassName()}>
      <div className={cn(workspaceUnifiedPanelClassName(), "flex-col")}>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-5 py-6 sm:px-6 sm:py-7">
          {hasMessages ? (
            <div className="w-full flex-1">
              <ChatMessageList messages={messages} streamingReply={streamingReply} />
            </div>
          ) : (
            <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-6 py-8 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="size-5" />
              </span>
              <div>
                <h2 className="text-xl font-semibold tracking-tight">Ask your first question</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Start with one of these report-grounded prompts.
                </p>
              </div>
              <SuggestedPrompts prompts={suggestedPrompts} onSelect={handleSend} disabled={isSending} />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="shrink-0 px-5 pb-5 sm:px-6 sm:pb-6">
          <div className="mx-auto w-full max-w-4xl">
            <ChatInput hasSentFirstMessage={hasMessages} disabled={isSending} onSend={handleSend} />
          </div>
        </div>
      </div>
    </div>
  )
}
