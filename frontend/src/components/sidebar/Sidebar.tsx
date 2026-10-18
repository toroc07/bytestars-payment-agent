import { Plus, ScrollText, Search, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, useParams } from 'react-router'
import { isOffline } from '@/api/client'
import { useConversations, useInvoices } from '@/api/hooks'
import type { ConversationSummary } from '@/api/types'
import { StatusGlyph } from '@/components/decision/StatusGlyph'
import { cn } from '@/lib/cn'
import { formatAmount, formatTimestamp } from '@/lib/format'
import { FILTERS, INVOICE_STATUS, NO_INVOICE, type SidebarFilter } from '@/lib/status'

function matches(c: ConversationSummary, filter: SidebarFilter) {
  const statuses = FILTERS.find((f) => f.id === filter)?.statuses
  return !statuses || (c.invoice_status != null && statuses.includes(c.invoice_status))
}

export function Sidebar({ onNavigate, onClose }: { onNavigate?: () => void; onClose?: () => void }) {
  const [filter, setFilter] = useState<SidebarFilter>('all')
  const [query, setQuery] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)
  const { conversationId } = useParams()
  const conversations = useConversations()
  const invoices = useInvoices()
  const invoiceById = useMemo(() => new Map((invoices.data ?? []).map((i) => [i.id, i])), [invoices.data])
  const list = conversations.data ?? []
  const needle = query.trim().toLowerCase()
  const visible = list
    .filter((c) => matches(c, filter))
    .filter((c) => {
      if (!needle) return true
      const e = c.invoice_id ? invoiceById.get(c.invoice_id)?.extracted : undefined
      return [c.title, e?.vendor_name, e?.invoice_number].some((s) => s?.toLowerCase().includes(needle))
    })
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  // "/" jumps to the search box from anywhere outside a text field.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      const typing = target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
      if (event.key === '/' && !typing && !event.metaKey && !event.ctrlKey) {
        event.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <nav aria-label="Historial de facturas" className="flex h-full flex-col bg-paper-deep">
      <div className="px-4 pt-5 pb-4">
        <div className="flex items-start justify-between gap-2">
          <Link to="/" onClick={onNavigate} className="block rounded-md">
            <span className="block text-[0.9375rem] font-semibold tracking-tight">ByteStars Payment Agent</span>
            <span className="block text-xs text-ink-muted">Pagos simulados con reglas</span>
          </Link>
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar historial"
              className="pressable -mt-1 -mr-1 grid size-9 shrink-0 place-items-center rounded-lg text-ink-muted hover:bg-paper hover:text-ink"
            >
              <X className="size-4" />
            </button>
          ) : null}
        </div>
        <Link
          to="/"
          onClick={onNavigate}
          className="pressable mt-4 flex h-10 items-center justify-center gap-2 rounded-lg bg-intaglio text-sm font-medium text-paper hover:bg-intaglio-deep"
        >
          <Plus className="size-4" aria-hidden="true" />
          Nueva factura
        </Link>
      </div>

      <div className="px-3 pb-2">
        <label htmlFor="sidebar-search" className="sr-only">
          Buscar factura
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
          <input
            id="sidebar-search"
            ref={searchRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar proveedor o factura"
            aria-describedby="sidebar-search-hint"
            className="h-9 w-full rounded-lg bg-paper/70 pr-8 pl-8 text-sm text-ink shadow-[inset_0_0_0_1px_var(--color-rule)] placeholder:text-ink-muted focus-visible:shadow-[inset_0_0_0_2px_var(--color-intaglio)] focus-visible:outline-none"
          />
          <kbd
            id="sidebar-search-hint"
            className="tabular pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 rounded border border-rule px-1 text-xs text-ink-muted"
            aria-label="Atajo: tecla barra"
          >
            /
          </kbd>
        </div>
      </div>

      <div className="px-3" role="group" aria-label="Filtrar por estado">
        <div className="grid grid-cols-2 gap-0.5 rounded-lg bg-paper/70 p-0.5">
          {FILTERS.map((f) => {
            const count = list.filter((c) => matches(c, f.id)).length
            const active = filter === f.id
            return (
              <button
                key={f.id}
                type="button"
                aria-pressed={active}
                title={f.id === 'blocked' ? 'Rechazadas por el agente o por una persona' : undefined}
                onClick={() => setFilter(f.id)}
                className={cn(
                  'rounded-md px-1 py-1.5 text-xs font-medium text-ink-muted transition-colors duration-150 hover:text-ink',
                  active &&
                    'bg-sheet text-ink shadow-[0_1px_2px_rgb(30_28_24/0.12),inset_0_0_0_1px_var(--color-rule)]',
                )}
              >
                {f.label}
                {count > 0 && f.id !== 'all' ? (
                  <>
                    <span className="sr-only">, </span>
                    <span className="tabular ml-1">{count}</span>
                  </>
                ) : null}
              </button>
            )
          })}
        </div>
      </div>

      <div className="mt-3 min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {conversations.isPending ? (
          <div className="space-y-2 px-2 pt-1" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="ink-pulse h-11 rounded-lg bg-paper/70" />
            ))}
          </div>
        ) : conversations.isError ? (
          <p className="px-3 py-2 text-sm leading-relaxed text-ink-muted">
            {isOffline(conversations.error)
              ? 'Sin conexión con el servidor. El historial aparecerá cuando vuelva.'
              : conversations.error.message}
          </p>
        ) : visible.length === 0 ? (
          <p className="px-3 py-2 text-sm leading-relaxed text-ink-muted">
            {list.length === 0
              ? 'Aún no hay facturas. Las que proceses aparecerán aquí con su estado.'
              : needle
                ? `Ninguna factura coincide con «${query.trim()}».`
                : 'Ninguna factura con este estado.'}
          </p>
        ) : (
          <ul className="space-y-0.5">
            {visible.map((c) => {
              const meta = c.invoice_status
                ? INVOICE_STATUS[c.invoice_status]
                : c.invoice_id
                  ? INVOICE_STATUS.received
                  : NO_INVOICE
              const dimmed = Boolean(conversationId) && c.id !== conversationId
              const e = c.invoice_id ? invoiceById.get(c.invoice_id)?.extracted : undefined
              const amount = formatAmount(e?.amount, e?.currency)
              return (
                <li key={c.id}>
                  <NavLink
                    to={`/c/${c.id}`}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        'grid grid-cols-[0.875rem_1fr_auto] items-center gap-x-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors duration-150 hover:bg-paper/80',
                        isActive && 'bg-sheet shadow-[inset_0_0_0_1px_var(--color-rule-strong)]',
                      )
                    }
                  >
                    <StatusGlyph shape={meta.shape} tone={meta.tone} />
                    <span className="min-w-0">
                      <span className={cn('block truncate font-medium', dimmed ? 'text-ink-soft' : 'text-ink')}>
                        {e?.vendor_name ?? c.title}
                      </span>
                      <span className="block truncate text-xs text-ink-muted">
                        {meta.label} · <span className="tabular">{formatTimestamp(c.updated_at)}</span>
                      </span>
                    </span>
                    <span className="tabular self-start pt-0.5 text-right text-xs text-ink-soft">
                      {amount ? (
                        <>
                          <span className="block text-ink-muted">{e?.currency}</span>
                          {amount}
                        </>
                      ) : null}
                    </span>
                  </NavLink>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="border-t border-rule px-3 py-3">
        <NavLink
          to="/registro"
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-ink-soft transition-colors duration-150 hover:bg-paper/80 hover:text-ink',
              isActive && 'bg-sheet text-ink shadow-[inset_0_0_0_1px_var(--color-rule-strong)]',
            )
          }
        >
          <ScrollText className="size-4" aria-hidden="true" />
          Registro de decisiones
        </NavLink>
      </div>
    </nav>
  )
}
