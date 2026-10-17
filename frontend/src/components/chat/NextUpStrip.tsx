import { ArrowRight } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { useConversations, useSummary } from '@/api/hooks'
import { StatusGlyph } from '@/components/decision/StatusGlyph'

/** "Lo siguiente": the single next thing the operator owes, always above the chat. */
export function NextUpStrip() {
  const { conversationId } = useParams()
  const summary = useSummary()
  const conversations = useConversations()

  const pending = (conversations.data ?? []).filter((c) => c.invoice_status === 'pending_approval')
  const count = summary.data?.pending_count ?? pending.length
  if (count === 0 || pending.length === 0) return null

  const next = pending.find((c) => c.id !== conversationId) ?? pending[0]
  const onlyThisOne = pending.length === 1 && next.id === conversationId

  return (
    <section
      aria-label="Lo siguiente"
      className="flex items-center justify-between gap-3 rounded-lg bg-ochre-tint px-4 py-2.5 text-sm text-ochre shadow-[inset_0_0_0_1px_var(--color-ochre-rule)]"
    >
      <span className="flex min-w-0 items-center gap-2">
        <StatusGlyph shape="ring" tone="ochre" />
        <span className="truncate">
          {count === 1 ? '1 factura espera tu aprobación' : `${count} facturas esperan tu aprobación`}
          {onlyThisOne ? ': es esta.' : ''}
        </span>
      </span>
      {onlyThisOne ? null : (
        <Link
          to={`/c/${next.id}`}
          className="pressable inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 font-semibold hover:bg-ochre-rule/40"
        >
          Revisar
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      )}
    </section>
  )
}
