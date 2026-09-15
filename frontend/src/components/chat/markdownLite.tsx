import { Fragment, type ReactNode } from "react"

/**
 * Minimal markdown renderer -- bold (**text**), bullet lists ("- "/"* "
 * lines), and paragraphs only. Not full CommonMark: the AI Beauty
 * Assistant's system prompt only ever asks for bold text and bullet lists
 * (see Backend/app/services/chat_service.py's _build_system_prompt), so a
 * small custom renderer avoids a new npm dependency for a narrow need --
 * same "build the small thing ourselves" posture as BeforeAfterSlider.
 */
export function renderMarkdownLite(content: string): ReactNode {
  const lines = content.split("\n")
  const blocks: ReactNode[] = []
  let currentList: string[] = []
  let paragraphLines: string[] = []

  const flushParagraph = (key: string) => {
    if (paragraphLines.length === 0) return
    blocks.push(
      <p key={key} className="leading-relaxed">
        {renderInline(paragraphLines.join(" "), key)}
      </p>
    )
    paragraphLines = []
  }

  const flushList = (key: string) => {
    if (currentList.length === 0) return
    blocks.push(
      <ul key={key} className="list-disc space-y-1 pl-5 leading-relaxed">
        {currentList.map((item, index) => (
          <li key={`${key}-${index}`}>{renderInline(item, `${key}-${index}`)}</li>
        ))}
      </ul>
    )
    currentList = []
  }

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim()
    const bulletMatch = /^[-*]\s+(.*)$/.exec(line)
    if (bulletMatch) {
      flushParagraph(`p-${index}`)
      currentList.push(bulletMatch[1])
      return
    }
    if (line === "") {
      flushParagraph(`p-${index}`)
      flushList(`ul-${index}`)
      return
    }
    flushList(`ul-${index}`)
    paragraphLines.push(line)
  })
  flushParagraph("p-end")
  flushList("ul-end")

  return <div className="space-y-2">{blocks}</div>
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter((part) => part !== "")
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={`${keyPrefix}-b-${index}`}>{part.slice(2, -2)}</strong>
      }
      return <Fragment key={`${keyPrefix}-t-${index}`}>{part}</Fragment>
    })
}
