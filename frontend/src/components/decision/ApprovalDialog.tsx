import { X } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { useResolveInvoice } from '@/api/hooks'
import type { RuleCheck } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Field, Input, Textarea } from '@/components/ui/field'

/**
 * A person resolves an escalation. The dialog keeps the evidence in view (the rules that failed, observed
 * against expected), says the payment is simulated, and requires a name and a reason for the audit trail.
 * The name is typed every time on purpose: a remembered name would let anyone at this browser approve as
 * someone else without noticing.
 */
export function ApprovalDialog({
  invoiceId,
  action,
  open,
  onOpenChange,
  beneficiary,
  amountLabel,
  failedChecks,
}: {
  invoiceId: string
  action: 'approve' | 'reject'
  open: boolean
  onOpenChange: (open: boolean) => void
  beneficiary: string
  amountLabel: string | null
  failedChecks: RuleCheck[]
}) {
  const [approver, setApprover] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)
  const [comment, setComment] = useState('')
  const [tried, setTried] = useState(false)
  const resolve = useResolveInvoice(invoiceId)
  const approving = action === 'approve'
  const missingName = approver.trim() === ''
  const missingComment = comment.trim() === ''

  function submit(event: FormEvent) {
    event.preventDefault()
    setTried(true)
    if (missingName || missingComment) return
    resolve.mutate(
      { action, approver: approver.trim(), comment: comment.trim() },
      {
        onSuccess: () => {
          setComment('')
          onOpenChange(false)
        },
      },
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) resolve.reset()
        onOpenChange(next)
      }}
    >
      <DialogContent
        className="max-w-lg"
        onOpenAutoFocus={(event) => {
          event.preventDefault()
          nameRef.current?.focus()
        }}
        title={approving ? `Aprobar excepción: ${beneficiary}` : `Rechazar: ${beneficiary}`}
        description={
          <>
            {amountLabel ? <span className="tabular font-medium text-ink">{amountLabel}</span> : null}
            {amountLabel ? ' · ' : null}
            {approving
              ? 'Pago simulado: no se mueve dinero, pero tu aprobación queda registrada.'
              : 'La factura no se pagará y tu decisión queda registrada.'}
          </>
        }
      >
        <form onSubmit={submit} className="grid gap-4">
          {failedChecks.length > 0 ? (
            <section aria-labelledby="failed-title" className="rounded-lg bg-paper px-4 py-3 ring-1 ring-rule">
              <h3 id="failed-title" className="text-sm font-semibold">
                {approving ? 'Estás aprobando a pesar de que:' : 'El agente la dejó por aprobar porque:'}
              </h3>
              <ul className="mt-2 space-y-2">
                {failedChecks.map((check, i) => (
                  <li key={`${check.rule_id}-${i}`} className="grid grid-cols-[1rem_1fr] gap-x-2 text-sm">
                    <X
                      className={
                        check.outcome_if_failed === 'block' ? 'mt-0.5 size-4 text-brick' : 'mt-0.5 size-4 text-ochre'
                      }
                      aria-hidden="true"
                    />
                    <span>
                      {check.message}
                      {check.observed || check.expected ? (
                        <span className="mt-1 grid grid-cols-[auto_1fr] gap-x-2 text-xs text-ink-muted">
                          {check.observed ? (
                            <>
                              <span>Observado</span>
                              <span className="tabular text-ink-soft">{check.observed}</span>
                            </>
                          ) : null}
                          {check.expected ? (
                            <>
                              <span>Esperado</span>
                              <span className="tabular text-ink-soft">{check.expected}</span>
                            </>
                          ) : null}
                        </span>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <Field label="Tu nombre" htmlFor="approver" error={tried && missingName ? 'Escribe tu nombre.' : undefined}>
            <Input
              ref={nameRef}
              id="approver"
              autoComplete="name"
              value={approver}
              onChange={(e) => setApprover(e.target.value)}
              aria-invalid={tried && missingName}
              required
            />
          </Field>
          <Field
            label="Motivo"
            htmlFor="approval-comment"
            hint={approving ? 'Por qué apruebas esta excepción. Queda en el registro.' : 'Por qué no debe pagarse.'}
            error={tried && missingComment ? 'Explica el motivo: queda en el registro de la factura.' : undefined}
          >
            <Textarea
              id="approval-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              aria-invalid={tried && missingComment}
              aria-describedby={tried && missingComment ? 'approval-comment-error' : 'approval-comment-hint'}
              required
            />
          </Field>
          {resolve.error ? (
            <p role="alert" className="rounded-lg bg-brick-tint px-3 py-2 text-sm text-brick">
              No se pudo registrar tu decisión: {resolve.error.message}
            </p>
          ) : null}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" variant={approving ? 'primary' : 'danger'} disabled={resolve.isPending}>
              {resolve.isPending ? 'Registrando…' : approving ? 'Aprobar pago' : 'Rechazar pago'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
