import { Check, ChevronDown, Download, Minus, X } from 'lucide-react'
import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext } from 'react-router'
import { isOffline } from '@/api/client'
import { useConversations, useDecisions, useInvoices, useRules, useSummary } from '@/api/hooks'
import type { Decision, Invoice, Outcome, Summary } from '@/api/types'
import type { ShellContext } from '@/components/AppShell'
import { StatusGlyph } from '@/components/decision/StatusGlyph'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'
import { formatAmount, formatTimestamp } from '@/lib/format'
import { OUTCOME, verdictOf } from '@/lib/status'

type OutcomeFilter = 'all' | Outcome

/** Hatching for money a person approved, so the two segments differ in form and not only in colour. */
const PEOPLE_HATCH =
  'repeating-linear-gradient(135deg, var(--color-intaglio) 0 3px, var(--color-intaglio-tint) 3px 6px)'

/**
 * Period spend as a tape against the weekly review threshold (R09): past it the agent stops paying on its own
 * and every new invoice goes to a person. What the agent paid inside the rules and what people approved as an
 * exception are separate segments, so an approved exception never reads as the agent breaking a rule.
 * `period_budget` is not shown: no rule enforces it (docs/DECISION_ENGINE.md), so the UI must not claim it does.
 */
function PeriodTape({ summary, currency }: { summary: Summary; currency: string }) {
  const spent = Number(summary.spent_in_period)
  const byPeople = Number(summary.spent_by_people ?? 0)
  const byAgent = summary.spent_by_agent !== undefined ? Number(summary.spent_by_agent) : spent - byPeople
  const threshold = Number(summary.period_limit)
  const scale = Math.max(spent, threshold, 1)
  const pct = (n: number) => `${Math.min(100, (n / scale) * 100)}%`
  const money = (n: number) => `${currency} ${formatAmount(n, currency)}`

  return (
    <section aria-labelledby="tape-title" className="min-w-0 rounded-xl bg-sheet px-5 py-4 ring-1 ring-rule">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="tape-title" className="text-sm font-semibold">
          Gasto de los últimos 7 días
        </h2>
        <p className="text-sm">
          <span className="tabular">{money(spent)}</span> <span className="text-ink-muted">pagados</span>
        </p>
      </div>
      <div
        className="relative mt-3 flex h-3 overflow-visible rounded-full bg-paper-deep"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={scale}
        aria-valuenow={spent}
        aria-valuetext={`${money(byAgent)} pagados por el agente dentro de las reglas y ${money(byPeople)} aprobados por personas; umbral de revisión semanal ${money(threshold)}`}
        aria-label="Gasto de los últimos 7 días"
      >
        <div
          className="h-full rounded-l-full bg-intaglio transition-[width] duration-500 last:rounded-r-full"
          style={{ width: pct(byAgent) }}
        />
        {byPeople > 0 ? (
          <div
            className="h-full rounded-r-full transition-[width] duration-500"
            style={{ width: pct(byPeople), backgroundImage: PEOPLE_HATCH }}
          />
        ) : null}
        <span className="absolute -top-1 h-5 w-0.5 bg-ochre" style={{ left: pct(threshold) }} aria-hidden="true" />
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-xs text-ink-muted sm:flex sm:flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 shrink-0 rounded-sm bg-intaglio" aria-hidden="true" />
          <dt>Pagado por el agente, dentro de las reglas</dt>
          <dd className="tabular ml-auto whitespace-nowrap text-ink-soft sm:ml-0">{money(byAgent)}</dd>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 shrink-0 rounded-sm" style={{ backgroundImage: PEOPLE_HATCH }} aria-hidden="true" />
          <dt>Excepciones aprobadas por personas</dt>
          <dd className="tabular ml-auto whitespace-nowrap text-ink-soft sm:ml-0">{money(byPeople)}</dd>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-0.5 shrink-0 bg-ochre" aria-hidden="true" />
          <dt>Umbral de revisión semanal</dt>
          <dd className="tabular ml-auto whitespace-nowrap text-ink-soft sm:ml-0">{money(threshold)}</dd>
        </div>
      </dl>
      <p className="mt-2 text-xs text-ink-muted">
        Por encima del umbral, el agente ya no paga solo: cada factura nueva va a una persona, que la aprueba o la
        rechaza con su nombre y un motivo.
      </p>
    </section>
  )
}

function csvCell(value: unknown) {
  const text = value === null || value === undefined ? '' : String(value)
  return /[",\n;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function exportCsv(rows: Decision[], invoices: Map<string, Invoice>) {
  const header = [
    'fecha',
    'factura_id',
    'beneficiario',
    'numero_factura',
    'monto',
    'moneda',
    'resultado',
    'decidido_por',
    'aprobador',
    'comentario',
    'version_reglas',
    'reglas_sin_cumplir',
    'resumen',
  ]
  const lines = rows.map((d) => {
    const e = invoices.get(d.invoice_id)?.extracted
    return [
      d.created_at,
      d.invoice_id,
      e?.vendor_name,
      e?.invoice_number,
      e?.amount,
      e?.currency,
      verdictOf(d.outcome, d.actor),
      d.actor === 'human' ? 'persona' : 'agente',
      d.approver,
      d.comment,
      d.rule_set_version,
      d.checks
        .filter((c) => c.status === 'failed')
        .map((c) => c.rule_id)
        .join(' '),
      d.summary,
    ]
      .map(csvCell)
      .join(',')
  })
  const blob = new Blob([[header.join(','), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `registro-decisiones-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

/** The stub of one decision, unfolded inside the log. */
function ChecksDetail({ decision }: { decision: Decision }) {
  if (decision.checks.length === 0)
    return <p className="text-sm text-ink-muted">No se evaluaron reglas para esta decisión.</p>
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {decision.checks.map((c, i) => {
        const failed = c.status === 'failed'
        const Icon = failed ? X : c.status === 'skipped' ? Minus : Check
        const tone = failed ? (c.outcome_if_failed === 'block' ? 'text-brick' : 'text-ochre') : c.status === 'skipped' ? 'text-ink-muted' : 'text-intaglio'
        return (
          <li key={`${c.rule_id}-${i}`} className="grid grid-cols-[1rem_1fr] gap-x-2 text-sm">
            <Icon className={cn('mt-0.5 size-4', tone)} aria-hidden="true" strokeWidth={2.5} />
            <span>
              <span className="sr-only">{failed ? 'No cumple' : c.status === 'skipped' ? 'No aplica' : 'Cumple'}: </span>
              {c.message}
              {c.observed || c.expected ? (
                <span className="tabular block text-xs text-ink-muted">
                  {c.observed ? `Observado: ${c.observed}` : ''}
                  {c.observed && c.expected ? ' · ' : ''}
                  {c.expected ? `Esperado: ${c.expected}` : ''}
                </span>
              ) : null}
              <span className="tabular block text-xs text-ink-muted">
                <span className="sr-only">Regla </span>
                {c.rule_id}
              </span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}

const FILTERS: { id: OutcomeFilter; label: string }[] = [
  { id: 'all', label: 'Todas' },
  { id: 'pay', label: 'Pagadas' },
  { id: 'escalate', label: 'Por aprobar' },
  { id: 'block', label: 'Rechazadas' },
]

export function LogPage() {
  const { setTitle } = useOutletContext<ShellContext>()
  useEffect(() => setTitle('Registro'), [setTitle])

  const decisions = useDecisions()
  const invoices = useInvoices()
  const conversations = useConversations()
  const summary = useSummary()
  const rules = useRules()
  const [filter, setFilter] = useState<OutcomeFilter>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const baseCurrency = rules.data?.base_currency ?? 'USD'

  const invoiceById = useMemo(() => new Map((invoices.data ?? []).map((i) => [i.id, i])), [invoices.data])
  const conversationByInvoice = useMemo(
    () => new Map((conversations.data ?? []).filter((c) => c.invoice_id).map((c) => [c.invoice_id!, c.id])),
    [conversations.data],
  )
  const rows = useMemo(
    () =>
      [...(decisions.data ?? [])]
        .filter((d) => filter === 'all' || d.outcome === filter)
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [decisions.data, filter],
  )

  return (
    <div className="h-full overflow-x-hidden overflow-y-auto">
      <div className="mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)] gap-6 px-4 py-6 sm:px-6 sm:py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight">Registro de decisiones</h1>
            <p className="mt-1 max-w-[60ch] text-sm text-ink-soft">
              Cada decisión del agente y de las personas, con las reglas que la explican. Las decisiones no se
              editan: una aprobación agrega una fila nueva.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            disabled={rows.length === 0}
            onClick={() => exportCsv(rows, invoiceById)}
          >
            <Download />
            Exportar CSV
            {rows.length > 0 ? (
              <span className="tabular text-ink-muted">
                ({rows.length} {rows.length === 1 ? 'fila' : 'filas'}
                {filter === 'all' ? '' : ' filtradas'})
              </span>
            ) : null}
          </Button>
        </div>

        {summary.data ? (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <PeriodTape summary={summary.data} currency={baseCurrency} />
            <dl className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl bg-sheet px-5 py-4 text-sm ring-1 ring-rule">
              {(
                [
                  ['Pagadas', summary.data.paid_count, 'disc', 'intaglio'],
                  ['Por aprobar', summary.data.pending_count, 'ring', 'ochre'],
                  ['Rechazadas', summary.data.blocked_count, 'square', 'brick'],
                ] as const
              ).map(([label, count, shape, tone]) => (
                <div key={label} className="flex items-center gap-2">
                  <StatusGlyph shape={shape} tone={tone} />
                  <dt className="text-ink-soft">{label}</dt>
                  <dd className="tabular font-medium">{count}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}

        <div role="group" aria-label="Filtrar por resultado del agente" className="flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              aria-pressed={filter === f.id}
              onClick={() => setFilter(f.id)}
              className={cn(
                'pressable rounded-lg px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-paper-deep hover:text-ink',
                filter === f.id && 'bg-sheet text-ink shadow-[inset_0_0_0_1px_var(--color-rule-strong)]',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {decisions.isPending ? (
          <div className="ink-pulse h-48 rounded-xl bg-paper-deep" aria-hidden="true" />
        ) : decisions.isError ? (
          <p role="alert" className="rounded-lg bg-brick-tint px-4 py-3 text-sm text-brick">
            {isOffline(decisions.error)
              ? 'Sin conexión con el servidor. El registro aparecerá cuando vuelva.'
              : `No se pudo cargar el registro: ${decisions.error.message}`}
          </p>
        ) : rows.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-rule-strong px-6 py-10 text-center">
            <p className="font-medium">
              {decisions.data.length === 0 ? 'Todavía no hay decisiones.' : 'Ninguna decisión con este resultado.'}
            </p>
            <p className="mt-1 text-sm text-ink-muted">
              {decisions.data.length === 0 ? (
                <>
                  Cuando el agente procese una factura, su decisión quedará aquí.{' '}
                  <Link to="/" className="font-medium text-intaglio underline">
                    Revisar una factura
                  </Link>
                </>
              ) : (
                'Prueba con otro filtro.'
              )}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl bg-sheet ring-1 ring-rule">
            <table className="w-full text-left text-sm md:min-w-[56rem]">
              <caption className="sr-only">Decisiones registradas, de la más reciente a la más antigua</caption>
              <thead className="border-b border-rule text-xs text-ink-muted">
                <tr>
                  <th scope="col" className="w-10 px-2 py-3">
                    <span className="sr-only">Detalle</span>
                  </th>
                  <th scope="col" className="hidden px-4 py-3 font-medium sm:table-cell">Fecha</th>
                  <th scope="col" className="px-3 py-3 font-medium sm:px-4">Beneficiario</th>
                  <th scope="col" className="px-3 py-3 text-right font-medium sm:px-4">Monto</th>
                  <th scope="col" className="hidden px-4 py-3 font-medium sm:table-cell">Resultado</th>
                  <th scope="col" className="hidden px-4 py-3 font-medium md:table-cell">Decidido por</th>
                  <th scope="col" className="hidden px-4 py-3 font-medium md:table-cell">Reglas</th>
                  <th scope="col" className="hidden px-4 py-3 font-medium md:table-cell">Por qué</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => {
                  const e = invoiceById.get(d.invoice_id)?.extracted
                  const meta = OUTCOME[d.outcome]
                  const failed = d.checks.filter((c) => c.status === 'failed').length
                  const convo = conversationByInvoice.get(d.invoice_id)
                  const isOpen = expanded === d.id
                  const detailId = `detail-${d.id}`
                  return (
                    <Fragment key={d.id}>
                      <tr className="border-t border-rule align-top transition-colors duration-150 first:border-t-0 hover:bg-paper/60">
                        <td className="px-2 py-2.5">
                          <button
                            type="button"
                            aria-expanded={isOpen}
                            aria-controls={detailId}
                            onClick={() => setExpanded(isOpen ? null : d.id)}
                            className="pressable grid size-8 place-items-center rounded-md text-ink-muted hover:bg-paper-deep hover:text-ink"
                            aria-label={isOpen ? 'Ocultar reglas' : 'Ver reglas'}
                          >
                            <ChevronDown
                              className={cn('size-4 transition-transform duration-200', isOpen && 'rotate-180')}
                              aria-hidden="true"
                            />
                          </button>
                        </td>
                        <td className="tabular hidden px-4 py-3 whitespace-nowrap text-ink-soft sm:table-cell">
                          {formatTimestamp(d.created_at)}
                        </td>
                        <td className="px-3 py-3 sm:max-w-56 sm:px-4">
                          {convo ? (
                            <Link to={`/c/${convo}`} className="font-medium hover:underline">
                              {e?.vendor_name ?? 'No identificado'}
                            </Link>
                          ) : (
                            <span className="font-medium">{e?.vendor_name ?? 'No identificado'}</span>
                          )}
                          {e?.invoice_number ? (
                            <span className="tabular block text-xs text-ink-muted">{e.invoice_number}</span>
                          ) : null}
                          {/* On phones the date and result columns fold in here. */}
                          <span className="mt-1.5 flex items-center gap-1.5 text-xs text-ink-soft sm:hidden">
                            <StatusGlyph shape={meta.shape} tone={meta.tone} />
                            <span>
                              {verdictOf(d.outcome, d.actor)} ·{' '}
                              <span className="tabular">{formatTimestamp(d.created_at)}</span>
                            </span>
                          </span>
                        </td>
                        <td className="tabular px-3 py-3 text-right whitespace-nowrap sm:px-4">
                          {e?.amount ? (
                            <>
                              <span className="text-ink-muted">{e.currency}</span>{' '}
                              {formatAmount(e.amount, e.currency)}
                            </>
                          ) : (
                            <span className="text-ink-muted">—</span>
                          )}
                        </td>
                        <td className="hidden px-4 py-3 whitespace-nowrap sm:table-cell">
                          <span className="inline-flex items-center gap-2">
                            <StatusGlyph shape={meta.shape} tone={meta.tone} />
                            {verdictOf(d.outcome, d.actor)}
                          </span>
                        </td>
                        <td className="hidden px-4 py-3 whitespace-nowrap text-ink-soft md:table-cell">
                          {d.actor === 'human' ? (d.approver ?? 'Una persona') : 'Agente'}
                        </td>
                        <td className="hidden px-4 py-3 whitespace-nowrap text-ink-soft md:table-cell">
                          <span className="tabular">v{d.rule_set_version}</span> ·{' '}
                          <span className="tabular">
                            {failed}/{d.checks.length}
                          </span>{' '}
                          sin cumplir
                        </td>
                        <td className="hidden max-w-md px-4 py-3 text-ink-soft md:table-cell">
                          {d.comment ? `«${d.comment}» ` : ''}
                          {d.summary}
                        </td>
                      </tr>
                      {isOpen ? (
                        <tr id={detailId} className="bg-paper/50">
                          <td />
                          <td colSpan={7} className="px-4 pt-1 pb-4">
                            {/* On small screens the hidden columns live here. */}
                            <div className="mb-3 space-y-1 text-sm text-ink-soft md:hidden">
                              <p>
                                {d.comment ? `«${d.comment}» ` : ''}
                                {d.summary}
                              </p>
                              <p className="text-xs text-ink-muted">
                                Decidido por {d.actor === 'human' ? (d.approver ?? 'una persona') : 'el agente'} ·
                                reglas <span className="tabular">v{d.rule_set_version}</span>
                              </p>
                            </div>
                            <ChecksDetail decision={d} />
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
