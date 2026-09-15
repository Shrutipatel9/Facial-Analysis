"use client"

interface SuggestedPromptsProps {
  prompts: string[]
  onSelect: (prompt: string) => void
  disabled: boolean
}

/** Shown only while the conversation has no messages yet -- clicking a card sends it as the first message. */
export function SuggestedPrompts({ prompts, onSelect, disabled }: SuggestedPromptsProps) {
  if (prompts.length === 0) return null

  return (
    <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
      {prompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(prompt)}
          className="rounded-xl border border-border bg-white px-4 py-3.5 text-left text-sm leading-snug text-foreground shadow-sm transition-colors hover:border-primary/30 hover:bg-primary/[0.04] disabled:pointer-events-none disabled:opacity-50"
        >
          {prompt}
        </button>
      ))}
    </div>
  )
}
