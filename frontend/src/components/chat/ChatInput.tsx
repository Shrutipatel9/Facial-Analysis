"use client"

import { ArrowUp } from "lucide-react"
import { useState, type KeyboardEvent } from "react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface ChatInputProps {
  hasSentFirstMessage: boolean
  disabled: boolean
  onSend: (content: string) => void
}

export function ChatInput({ hasSentFirstMessage, disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState("")

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue("")
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-white px-2 py-1.5 shadow-sm">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={hasSentFirstMessage ? "Type your next question…" : "Ask anything"}
        maxLength={2000}
        rows={1}
        className="max-h-32 min-h-10 flex-1 resize-none border-0 bg-transparent px-4 py-2.5 text-sm shadow-none focus-visible:ring-0"
      />
      <Button
        type="button"
        size="icon"
        className="size-9 shrink-0 rounded-full"
        disabled={disabled || value.trim() === ""}
        onClick={handleSend}
        aria-label="Send message"
      >
        <ArrowUp className="size-4" />
      </Button>
    </div>
  )
}
