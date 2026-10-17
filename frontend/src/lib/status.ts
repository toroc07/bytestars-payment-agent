import type { InvoiceStatus, Outcome } from '@/api/types'

/** One physical form per state, never colour alone: filled disc, ring, square. */
export type StatusShape = 'disc' | 'ring' | 'square' | 'dotted'
export type StatusTone = 'intaglio' | 'ochre' | 'brick' | 'muted'

export interface StatusMeta {
  label: string
  shape: StatusShape
  tone: StatusTone
}

export const INVOICE_STATUS: Record<InvoiceStatus, StatusMeta> = {
  paid: { label: 'Pagada', shape: 'disc', tone: 'intaglio' },
  approved: { label: 'Aprobada por una persona', shape: 'disc', tone: 'intaglio' },
  pending_approval: { label: 'Por aprobar', shape: 'ring', tone: 'ochre' },
  blocked: { label: 'Rechazada por el agente', shape: 'square', tone: 'brick' },
  rejected: { label: 'Rechazada por una persona', shape: 'square', tone: 'brick' },
  received: { label: 'Recibida', shape: 'dotted', tone: 'muted' },
}

/** A conversation that never carried an invoice (a question answered with help). */
export const NO_INVOICE: StatusMeta = { label: 'Sin factura', shape: 'dotted', tone: 'muted' }

export const OUTCOME: Record<Outcome, StatusMeta & { verdict: string }> = {
  pay: { label: 'Pagar', verdict: 'Pagada', shape: 'disc', tone: 'intaglio' },
  escalate: { label: 'Escalar', verdict: 'Escalada a una persona', shape: 'ring', tone: 'ochre' },
  block: { label: 'Rechazar', verdict: 'Rechazada por el agente', shape: 'square', tone: 'brick' },
}

/** A human decision reads as approval or rejection, not as the agent's verdict. */
export function verdictOf(outcome: Outcome, actor: 'agent' | 'human'): string {
  if (actor === 'human') return outcome === 'pay' ? 'Aprobada por una persona' : 'Rechazada por una persona'
  return OUTCOME[outcome].verdict
}

export type SidebarFilter = 'all' | 'pending' | 'paid' | 'blocked'

export const FILTERS: { id: SidebarFilter; label: string; statuses: InvoiceStatus[] | null }[] = [
  { id: 'all', label: 'Todas', statuses: null },
  { id: 'pending', label: 'Por aprobar', statuses: ['pending_approval'] },
  { id: 'paid', label: 'Pagadas', statuses: ['paid', 'approved'] },
  { id: 'blocked', label: 'Rechazadas', statuses: ['blocked', 'rejected'] },
]
