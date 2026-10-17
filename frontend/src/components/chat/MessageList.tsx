import { FileText } from 'lucide-react'
import { useState } from 'react'
import type { ChatMessage } from '@/api/types'
import { DecisionThread } from '@/components/decision/DecisionCheque'
import { formatTimestamp } from '@/lib/format'

export interface PendingTurn {
  text?: string
  fileName?: string
}

const LONG_TEXT = 420

function UserBubble({ content, fileName, time }: { content?: string; fileName?: string; time?: string | null }) {
  const [expanded, setExpanded] = useState(false)
  const long = (content?.length ?? 0) > LONG_TEXT
  const shown = long && !expanded ? `${content!.slice(0, LONG_TEXT).trimEnd()}…` : content

  return (
    <div className="flex justify-end">
      <div className="max-w-[min(36rem,85%)] space-y-2 rounded-2xl rounded-br-md bg-paper-deep px-4 py-3 text-[0.9375rem] leading-relaxed">
        {fileName ? (
          <span className="inline-flex max-w-full items-center gap-2 rounded-md bg-sheet px-2 py-1 text-sm ring-1 ring-rule">
            <FileText className="size-4 shrink-0 text-ink-soft" aria-hidden="true" />
            <span className="truncate">{fileName}</span>
          </span>
        ) : null}
        {shown ? <p className="whitespace-pre-wrap break-words">{shown}</p> : null}
        {long ? (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="text-sm font-medium text-intaglio underline underline-offset-3"
          >
            {expanded ? 'Ver menos' : 'Ver todo'}
          </button>
        ) : null}
        {time ? <p className="tabular text-right text-[0.6875rem] text-ink-muted">{time}</p> : null}
      </div>
    </div>
  )
}

/** While the agent works: an unprinted cheque, nothing invented. */
function ReviewingCheque() {
  return (
    <div role="status" className="rounded-xl bg-sheet px-6 py-6 ring-1 ring-rule-strong">
      <p className="text-sm text-ink-soft">Revisando la factura y aplicando las reglas…</p>
      <div className="mt-4 space-y-3" aria-hidden="true">
        <div className="ink-pulse h-4 w-40 rounded bg-paper-deep" />
        <div className="ink-pulse h-10 w-64 rounded bg-paper-deep" />
        <div className="ink-pulse h-7 w-28 rounded-full bg-paper-deep" />
      </div>
    </div>
  )
}

const FILE_PREFIX = 'Archivo adjunto: '

export function MessageList({
  messages,
  pending,
  freshMessageId,
}: {
  messages: ChatMessage[]
  pending: PendingTurn | null
  freshMessageId: string | null
}) {
  return (
    <ol className="space-y-8" aria-label="Conversación">
      {messages.map((message) => (
        <li key={message.id}>
          {message.role === 'user' ? (
            <UserBubble
              content={message.content.startsWith(FILE_PREFIX) ? undefined : message.content}
              fileName={
                message.content.startsWith(FILE_PREFIX) ? message.content.slice(FILE_PREFIX.length) : undefined
              }
              time={formatTimestamp(message.created_at)}
            />
          ) : message.decision ? (
            <DecisionThread decision={message.decision} fresh={message.id === freshMessageId} />
          ) : (
            <p className="max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-soft">{message.content}</p>
          )}
        </li>
      ))}
      {pending ? (
        <>
          <li>
            <UserBubble content={pending.text} fileName={pending.fileName} />
          </li>
          <li>
            <ReviewingCheque />
          </li>
        </>
      ) : null}
    </ol>
  )
}
