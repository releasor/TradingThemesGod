import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type Block =
  | { type: 'h1' | 'h2' | 'h3'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'code'; text: string }
  | { type: 'p'; text: string }

function inlineFormat(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let match: RegExpExecArray | null
  let key = 0
  while ((match = re.exec(text)) != null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index))
    }
    const token = match[0]
    if (token.startsWith('**')) {
      parts.push(
        <strong key={key++} className="font-semibold text-foreground">
          {token.slice(2, -2)}
        </strong>
      )
    } else {
      parts.push(
        <code
          key={key++}
          className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>
      )
    }
    last = match.index + token.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (line.startsWith('```')) {
      const buf: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        buf.push(lines[i])
        i++
      }
      blocks.push({ type: 'code', text: buf.join('\n') })
      i++
      continue
    }
    if (/^###\s+/.test(line)) {
      blocks.push({ type: 'h3', text: line.replace(/^###\s+/, '') })
      i++
      continue
    }
    if (/^##\s+/.test(line)) {
      blocks.push({ type: 'h2', text: line.replace(/^##\s+/, '') })
      i++
      continue
    }
    if (/^#\s+/.test(line)) {
      blocks.push({ type: 'h1', text: line.replace(/^#\s+/, '') })
      i++
      continue
    }
    if (/^[-*]\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''))
        i++
      }
      blocks.push({ type: 'ul', items })
      continue
    }
    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''))
        i++
      }
      blocks.push({ type: 'ol', items })
      continue
    }
    if (!line.trim()) {
      i++
      continue
    }
    const buf = [line]
    i++
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^#{1,3}\s+/.test(lines[i]) &&
      !/^[-*]\s+/.test(lines[i]) &&
      !/^\d+\.\s+/.test(lines[i]) &&
      !lines[i].startsWith('```')
    ) {
      buf.push(lines[i])
      i++
    }
    blocks.push({ type: 'p', text: buf.join(' ') })
  }
  return blocks
}

/** 轻量 Markdown 预览（标题/列表/代码块/粗体），无额外依赖 */
export function PromptMarkdownPreview({
  text,
  className = '',
  empty = '暂无内容',
}: {
  text: string
  className?: string
  empty?: string
}) {
  if (!text.trim()) {
    return (
      <div
        className={cn(
          'rounded-md border border-dashed border-border bg-muted/20 px-3 py-6 text-sm text-muted-foreground',
          className
        )}
      >
        {empty}
      </div>
    )
  }

  const blocks = parseBlocks(text)
  return (
    <div
      className={cn(
        'space-y-2 overflow-auto rounded-md border border-border bg-background px-3 py-2 text-sm leading-relaxed',
        className
      )}
      data-testid="prompt-markdown-preview"
    >
      {blocks.map((block, idx) => {
        if (block.type === 'h1') {
          return (
            <h3 key={idx} className="text-base font-semibold tracking-tight">
              {inlineFormat(block.text)}
            </h3>
          )
        }
        if (block.type === 'h2') {
          return (
            <h4 key={idx} className="text-sm font-semibold">
              {inlineFormat(block.text)}
            </h4>
          )
        }
        if (block.type === 'h3') {
          return (
            <h5 key={idx} className="text-sm font-medium text-foreground">
              {inlineFormat(block.text)}
            </h5>
          )
        }
        if (block.type === 'ul') {
          return (
            <ul key={idx} className="list-disc space-y-1 pl-5">
              {block.items.map((item, j) => (
                <li key={j}>{inlineFormat(item)}</li>
              ))}
            </ul>
          )
        }
        if (block.type === 'ol') {
          return (
            <ol key={idx} className="list-decimal space-y-1 pl-5">
              {block.items.map((item, j) => (
                <li key={j}>{inlineFormat(item)}</li>
              ))}
            </ol>
          )
        }
        if (block.type === 'code') {
          return (
            <pre
              key={idx}
              className="overflow-x-auto rounded-md bg-muted/50 p-2 font-mono text-xs"
            >
              {block.text}
            </pre>
          )
        }
        return (
          <p key={idx} className="text-foreground/90">
            {inlineFormat(block.text)}
          </p>
        )
      })}
    </div>
  )
}
