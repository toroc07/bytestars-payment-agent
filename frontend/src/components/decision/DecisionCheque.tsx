import { Check, ChevronDown, Minus, PenLine, RotateCcw, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useInvoice, useInvoiceDecisions, useReevaluate } from '@/api/hooks'
import type { Decision, Invoice, RuleCheck } from '@/api/types'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'
import { formatAmount, formatDate, formatTimestamp } from '@/lib/format'
import { OUTCOME, type StatusTone } from '@/lib/status'
import { buildThread, explanationNotes } from '@/lib/thread'
import { ApprovalDialog } from './ApprovalDialog'
import { Guilloche } from './Guilloche'
import { StatusGlyph } from './StatusGlyph'

const verdictTone: Record<StatusTone, string> = {
  intaglio: 'bg-intaglio text-paper',
  ochre: 'bg-ochre-tint text-ochre shadow-[inset_0_0_0_1px_var(--color-ochre-rule)]',
  brick: 'bg-brick-tint text-brick shadow-[inset_0_0_0_1px_var(--color-brick-rule)]',
  muted: 'bg-paper-deep text-ink-soft',
}

const MICROPRINT = 'SIMULADO · NO ES UN PAGO REAL · '.repeat(8)

/** Failed rules first (blocking before escalating), then the rest in catalogue order. */
function orderChecks(checks: RuleCheck[]) {
  const rank = (c: RuleCheck) => (c.status !== 'failed' ? 2 : c.outcome_if_failed === 'block' ? 0 : 1)
  return checks
    .map((c, i) => [c, i] as const)
    .sort((a, b) => rank(a[0]) - rank(b[0]) || a[1] - b[1])
    .map(([c]) => c)
}

function CheckRow({ check }: { check: RuleCheck }) {
  const failed = check.status === 'failed'
  const skipped = check.status === 'skipped'
  const Icon = failed ? X : skipped ? Minus : Check
  const tone = failed
    ? check.outcome_if_failed === 'block'
      ? 'text-brick'
      : 'text-ochre'
    : skipped
      ? 'text-ink-muted'
      : 'text-intaglio'
  const statusText = failed
    ? check.outcome_if_failed === 'block'
      ? 'No cumple · rechaza el pago'
      : 'No cumple · requiere aprobación'
    : skipped
      ? 'No aplica'
      : 'Cumple'

  return (
    <li
      className={cn(
        'grid grid-cols-[1.25rem_1fr] gap-x-2',
        failed
          ? cn('-mx-2 rounded-md px-2 py-2.5', check.outcome_if_failed === 'block' ? 'bg-brick-tint/50' : 'bg-ochre-tint/50')
          : 'py-2.5 first:pt-0 last:pb-0',
      )}
    >
      <Icon className={cn('mt-0.5 size-4', tone)} aria-hidden="true" strokeWidth={2.5} />
      <div className="min-w-0 space-y-1">
        <p className="text-sm leading-snug text-ink">
          <span className="sr-only">{statusText}: </span>
          {check.message}
        </p>
        {(check.observed || check.expected) && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-2 text-xs text-ink-muted">
            {check.observed ? (
              <>
                <dt>Observado</dt>
                <dd className="tabular break-words text-ink-soft">{check.observed}</dd>
              </>
            ) : null}
            {check.expected ? (
              <>
                <dt>Esperado</dt>
                <dd className="tabular break-words text-ink-soft">{check.expected}</dd>
              </>
            ) : null}
          </dl>
        )}
        <p className={cn('tabular text-xs', failed ? cn('font-semibold', tone) : 'text-ink-muted')}>
          <span className="sr-only">Regla </span>
          {check.rule_id}
          <span aria-hidden="true"> · {statusText}</span>
        </p>
      </div>
    </li>
  )
}

interface ChequeProps {
  decision: Decision
  invoice: Invoice | undefined
  invoicePending: boolean
  endorsement: Decision | null
  isLatest: boolean
  isReevaluation: boolean
  fresh: boolean
  onReevaluated: (decisionId: string) => void
}

function ChequeCard({
  decision,
  invoice,
  invoicePending,
  endorsement,
  isLatest,
  isReevaluation,
  fresh,
  onReevaluated,
}: ChequeProps) {
  const [dialog, setDialog] = useState<'approve' | 'reject' | null>(null)
  const ordered = orderChecks(decision.checks)
  const failing = ordered.filter((c) => c.status === 'failed')
  const passing = ordered.filter((c) => c.status !== 'failed')
  const passed = passing.filter((c) => c.status === 'passed').length
  const skipped = passing.length - passed
  // On a paid cheque the passing rules are the explanation; elsewhere the failures are, so fold the rest.
  const [showPassing, setShowPassing] = useState(decision.outcome === 'pay')
  const reevaluate = useReevaluate(decision.invoice_id)
  const ref = useRef<HTMLElement>(null)
  // The dialog is opened from a button on this cheque; focus goes back there when it closes, or to the
  // cheque itself when the button is gone (the invoice was just resolved).
  const opener = useRef<HTMLButtonElement | null>(null)
  useEffect(() => {
    if (dialog !== null || !opener.current) return
    const target = opener.current.isConnected ? opener.current : ref.current
    opener.current = null
    requestAnimationFrame(() => target?.focus())
  }, [dialog])

  // A cheque issued while the operator watches (a re-evaluation) is brought into view.
  useEffect(() => {
    if (fresh && isReevaluation) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [fresh, isReevaluation])

  const extracted = invoice?.extracted
  const outcome = OUTCOME[decision.outcome]
  // Once a person resolves it, the face shows the final state and the agent's verdict becomes history.
  const final = endorsement ? OUTCOME[endorsement.outcome === 'pay' ? 'pay' : 'block'] : outcome
  const approver = endorsement?.approver ?? 'una persona'
  const finalVerdict = endorsement
    ? endorsement.outcome === 'pay'
      ? `Pagada · la aprobó ${approver}`
      : `Rechazada por ${approver}`
    : outcome.verdict
  const beneficiary = extracted?.vendor_name ?? null
  const currency = extracted?.currency ?? null
  const amount = formatAmount(extracted?.amount, currency)
  const amountLabel = amount ? `${currency ?? ''} ${amount}`.trim() : null
  const failedChecks = decision.checks.filter((c) => c.status === 'failed')
  const failed = failedChecks.length

  // Actions live only on the cheque currently in force, and only where they make sense:
  // a human resolves an escalation; a blocked or pending invoice can be re-run after fixing its cause.
  const open = isLatest && !endorsement
  const canResolve = open && decision.outcome === 'escalate' && invoice?.status === 'pending_approval'
  const canReevaluate = open && (invoice?.status === 'blocked' || invoice?.status === 'pending_approval')
  // Nobody approves paying an unknown party or an unknown amount; it can still be rejected or re-run.
  const missing = [!beneficiary && 'el beneficiario', !amount && 'el monto'].filter(Boolean) as string[]
  const canApprove = canResolve && missing.length === 0
  const approveBlockedId = `approve-blocked-${decision.id}`

  return (
    <article
      ref={ref}
      aria-label={`${isReevaluation ? 'Reevaluación' : 'Decisión'}: ${finalVerdict}${beneficiary ? `, ${beneficiary}` : ''}`}
      data-cheque=""
      tabIndex={-1}
      className={cn('w-full scroll-mt-4', fresh && 'cheque-issue')}
    >
      {isReevaluation ? (
        <p className="mb-2 flex items-center gap-2 px-1 text-sm text-ink-muted">
          <RotateCcw className="size-4" aria-hidden="true" />
          Reevaluada con las reglas v{decision.rule_set_version}
        </p>
      ) : null}

      <div
        className={cn(
          'relative grid overflow-hidden rounded-xl bg-sheet shadow-[0_1px_0_var(--color-rule),0_12px_32px_-20px_rgb(30_28_24/0.4)] ring-1 ring-rule-strong md:grid-cols-[minmax(0,1fr)_19rem]',
        )}
      >
        {/* Face */}
        <div className="relative isolate px-5 pt-5 pb-9 sm:px-7 sm:pt-6">
          <Guilloche className="pointer-events-none absolute inset-x-0 top-14 -z-10 h-40 w-full" />
          <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
            <div className="min-w-0">
              <p className="text-xs text-ink-muted">Beneficiario</p>
              <p className={cn('truncate text-lg font-medium', !beneficiary && 'text-ink-muted')}>
                {invoicePending ? (
                  <span className="ink-pulse inline-block h-5 w-48 rounded bg-paper-deep align-middle" />
                ) : (
                  (beneficiary ?? 'Beneficiario no identificado')
                )}
              </p>
            </div>
            <dl className="grid grid-cols-[auto_auto] gap-x-3 text-right text-xs text-ink-muted">
              <dt>Factura</dt>
              <dd className="tabular text-ink-soft">{extracted?.invoice_number ?? '—'}</dd>
              <dt>Vence</dt>
              <dd className="tabular text-ink-soft">{formatDate(extracted?.due_date) ?? '—'}</dd>
              {extracted?.vendor_country ? (
                <>
                  <dt>País</dt>
                  <dd className="tabular text-ink-soft">{extracted.vendor_country}</dd>
                </>
              ) : null}
            </dl>
          </div>

          <p className="mt-6 flex items-baseline gap-2">
            {amount ? (
              <>
                <span className="tabular text-lg text-ink-muted">{currency}</span>
                <span className="tabular text-4xl font-medium tracking-tight sm:text-5xl">{amount}</span>
              </>
            ) : (
              <span className="text-2xl font-medium text-ink-muted">Monto no extraído</span>
            )}
          </p>
          <p className="mt-1 text-xs text-ink-muted">Pago simulado: no se mueve dinero real.</p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <span
              className={cn(
                'inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold',
                verdictTone[final.tone],
              )}
            >
              <StatusGlyph
                shape={final.shape}
                tone={final.tone === 'intaglio' ? 'muted' : final.tone}
                className={final.tone === 'intaglio' ? '[&_*]:fill-paper' : undefined}
              />
              {finalVerdict}
            </span>
            <span className="text-sm text-ink-muted">
              {endorsement ? (
                <>
                  <span className="tabular">{formatTimestamp(endorsement.created_at)}</span> · el agente la había
                  dejado en «{outcome.verdict}»
                </>
              ) : (
                <>Decidido por el agente · {formatTimestamp(decision.created_at)}</>
              )}
            </span>
          </div>
          {endorsement?.comment ? (
            <p className="mt-2 flex max-w-[50ch] gap-1.5 text-sm text-ink-soft">
              <PenLine className="mt-0.5 size-3.5 shrink-0 text-ink-muted" aria-hidden="true" />
              <span>«{endorsement.comment}»</span>
            </p>
          ) : null}
          {!isLatest && !endorsement ? (
            <p className="mt-3 text-sm text-ink-muted">Sustituida por la reevaluación de abajo.</p>
          ) : null}

          {canResolve || canReevaluate ? (
            <div className="mt-5 flex flex-wrap items-center gap-2">
              {canResolve ? (
                <>
                  <Button
                    variant="primary"
                    disabled={!canApprove}
                    aria-describedby={canApprove ? undefined : approveBlockedId}
                    onClick={(event) => {
                      opener.current = event.currentTarget
                      setDialog('approve')
                    }}
                  >
                    Aprobar pago
                  </Button>
                  <Button
                    variant="danger"
                    onClick={(event) => {
                      opener.current = event.currentTarget
                      setDialog('reject')
                    }}
                  >
                    Rechazar
                  </Button>
                </>
              ) : null}
              {canReevaluate ? (
                <Button
                  variant="secondary"
                  disabled={reevaluate.isPending}
                  onClick={() => reevaluate.mutate(undefined, { onSuccess: (d) => onReevaluated(d.id) })}
                >
                  <RotateCcw />
                  {reevaluate.isPending ? 'Reevaluando…' : 'Reevaluar con las reglas actuales'}
                </Button>
              ) : null}
            </div>
          ) : null}
          {canResolve && !canApprove ? (
            <p id={approveBlockedId} className="mt-2 max-w-[56ch] text-sm text-ink-soft">
              No se puede aprobar: falta {missing.join(' y ')}. Recházala o reevalúala cuando la factura traiga
              esos datos.
            </p>
          ) : null}
          {canReevaluate && !canResolve ? (
            <p className="mt-2 max-w-[52ch] text-xs text-ink-muted">
              Si corregiste la causa (por ejemplo, agregaste el beneficiario o su acuerdo), vuelve a evaluarla.
            </p>
          ) : null}
          {reevaluate.isError ? (
            <p role="alert" className="mt-3 text-sm text-brick">
              No se pudo reevaluar: {reevaluate.error.message}
            </p>
          ) : null}

          <p
            aria-hidden="true"
            className="tabular absolute inset-x-5 bottom-3 overflow-hidden whitespace-nowrap text-[0.625rem] tracking-[0.2em] text-ink-muted sm:inset-x-7"
          >
            {MICROPRINT}
          </p>
          <p className="sr-only">Pago simulado: no se movió dinero real.</p>
        </div>

        {/* Perforation + stub */}
        <div className="relative border-t-2 border-dashed border-rule-strong bg-paper/60 px-5 py-5 md:border-t-0 md:border-l-2 sm:px-6">
          <span
            aria-hidden="true"
            className="absolute -top-2.5 -left-2.5 hidden size-5 rounded-full bg-paper ring-1 ring-rule-strong md:block"
          />
          {endorsement ? null : (
            <span
              aria-hidden="true"
              className="absolute -bottom-2.5 -left-2.5 hidden size-5 rounded-full bg-paper ring-1 ring-rule-strong md:block"
            />
          )}
          <div className="mb-3 flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold">Por qué</h3>
            <p className="text-xs text-ink-muted">
              <span className="tabular">Reglas v{decision.rule_set_version}</span>
              {decision.checks.length > 0 ? (
                <>
                  {' · '}
                  <span className="tabular">
                    {failed}/{decision.checks.length}
                  </span>{' '}
                  sin cumplir
                </>
              ) : null}
            </p>
          </div>
          {decision.checks.length > 0 ? (
            <>
              {failing.length > 0 ? (
                <ul className="space-y-2">
                  {failing.map((check, i) => (
                    <CheckRow key={`${check.rule_id}-${i}`} check={check} />
                  ))}
                </ul>
              ) : null}
              {passing.length > 0 ? (
                <div className={cn(failing.length > 0 && 'mt-4 border-t border-rule pt-3')}>
                  <button
                    type="button"
                    className="pressable flex w-full items-center justify-between gap-2 rounded-md py-1 text-left text-sm text-ink-soft hover:text-ink"
                    aria-expanded={showPassing}
                    aria-controls={`passing-${decision.id}`}
                    onClick={() => setShowPassing((v) => !v)}
                  >
                    <span>
                      <span className="tabular">{passed}</span> {passed === 1 ? 'regla se cumple' : 'reglas se cumplen'}
                      {skipped > 0 ? (
                        <>
                          {' · '}
                          <span className="tabular">{skipped}</span> {skipped === 1 ? 'no aplica' : 'no aplican'}
                        </>
                      ) : null}
                    </span>
                    <ChevronDown
                      className={cn('size-4 shrink-0 transition-transform duration-200', showPassing && 'rotate-180')}
                      aria-hidden="true"
                    />
                  </button>
                  {showPassing ? (
                    <ul id={`passing-${decision.id}`} className="mt-3 divide-y divide-rule">
                      {passing.map((check, i) => (
                        <CheckRow key={`${check.rule_id}-${i}`} check={check} />
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-ink-muted">No se evaluaron reglas para esta decisión.</p>
          )}
        </div>

        {endorsement ? (
          <div
            className={cn(
              'flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-rule px-5 py-3 text-sm sm:px-7 md:col-span-2',
              endorsement.outcome === 'pay' ? 'bg-intaglio-tint/60' : 'bg-brick-tint/60',
            )}
          >
            <PenLine className="size-4 text-ink-soft" aria-hidden="true" />
            <span className="font-medium">
              {endorsement.outcome === 'pay' ? 'Aprobada' : 'Rechazada'} por {endorsement.approver ?? 'una persona'}
            </span>
            <span className="tabular text-xs text-ink-muted">{formatTimestamp(endorsement.created_at)}</span>
          </div>
        ) : null}
      </div>

      {(decision.summary || decision.explanation) && (
        <div className="mt-3 max-w-[50ch] space-y-2 px-1 text-[0.9375rem] leading-relaxed text-ink-soft">
          {decision.summary ? (
            <p>
              {endorsement ? <span className="text-ink-muted">Lo que decidió el agente: </span> : null}
              {decision.summary}
            </p>
          ) : null}
          {explanationNotes(decision).length > 0 ? (
            <ul className="space-y-1 text-sm text-ink-muted">
              {explanationNotes(decision).map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}

      {dialog ? (
        <ApprovalDialog
          invoiceId={decision.invoice_id}
          action={dialog}
          open
          onOpenChange={(isOpen) => !isOpen && setDialog(null)}
          beneficiary={beneficiary ?? 'Beneficiario no identificado'}
          amountLabel={amountLabel}
          failedChecks={failedChecks}
        />
      ) : null}
    </article>
  )
}

/**
 * The agent's answer to one invoice, issued as security cheques: the face says what happened and how
 * much, the perforated stub keeps every rule. Re-evaluations add cheques; people endorse them.
 */
export function DecisionThread({ decision, fresh = false }: { decision: Decision; fresh?: boolean }) {
  const invoiceQuery = useInvoice(decision.invoice_id)
  const historyQuery = useInvoiceDecisions(decision.invoice_id)
  const [freshId, setFreshId] = useState<string | null>(fresh ? decision.id : null)
  const thread = buildThread(decision, historyQuery.data)

  return (
    <div className="space-y-8">
      {thread.map((entry, i) => (
        <ChequeCard
          key={entry.decision.id}
          decision={entry.decision}
          invoice={invoiceQuery.data}
          invoicePending={invoiceQuery.isPending}
          endorsement={entry.endorsement}
          isLatest={i === thread.length - 1}
          isReevaluation={i > 0}
          fresh={entry.decision.id === freshId}
          onReevaluated={setFreshId}
        />
      ))}
    </div>
  )
}
