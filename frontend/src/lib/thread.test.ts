import { describe, expect, it } from 'vitest'
import type { Decision } from '@/api/types'
import { buildThread, explanationNotes } from './thread'

const decision = (id: string, created_at: string, patch: Partial<Decision> = {}): Decision => ({
  id,
  invoice_id: 'inv-1',
  outcome: 'escalate',
  actor: 'agent',
  checks: [],
  summary: '',
  rule_set_version: 1,
  created_at,
  ...patch,
})

describe('buildThread', () => {
  const start = decision('d1', '2026-10-17T10:00:00')

  it('returns only the starting decision when nothing happened after it', () => {
    expect(buildThread(start, [start])).toEqual([{ decision: start, endorsement: null }])
  })

  it('attaches a human approval as the endorsement of the cheque before it', () => {
    const human = decision('h1', '2026-10-17T10:05:00', { actor: 'human', outcome: 'pay', approver: 'Ana' })
    const thread = buildThread(start, [human, start])
    expect(thread).toHaveLength(1)
    expect(thread[0].endorsement?.id).toBe('h1')
  })

  it('turns a later agent decision into a new cheque (re-evaluation)', () => {
    const again = decision('d2', '2026-10-17T11:00:00', { outcome: 'pay' })
    const human = decision('h2', '2026-10-17T11:05:00', { actor: 'human', outcome: 'block' })
    const thread = buildThread(start, [human, again, start])
    expect(thread.map((e) => e.decision.id)).toEqual(['d1', 'd2'])
    expect(thread[0].endorsement).toBeNull()
    expect(thread[1].endorsement?.id).toBe('h2')
  })

  it('ignores decisions older than the one the message carries', () => {
    const older = decision('d0', '2026-10-17T09:00:00', { outcome: 'block' })
    expect(buildThread(start, [older, start]).map((e) => e.decision.id)).toEqual(['d1'])
  })
})

describe('explanationNotes', () => {
  it('keeps only how the invoice was read', () => {
    const explanation = [
      'Frenada: incumple una regla que no admite excepciones automáticas.',
      '• R03 · Proveedor no permitido: Delta Express no está en la lista.',
      'Reglas comprobadas: 9 cumplidas, 1 incumplidas, 1 sin aplicar.',
      'Datos leídos con el lector local (sin IA).',
      'No se movió dinero real: los pagos de esta demo son simulados.',
    ].join('\n')
    expect(explanationNotes({ summary: 'Rechazada: …', explanation })).toEqual([
      'Datos leídos con el lector local (sin IA).',
    ])
    const unread = 'Pendiente de aprobación.\nNo se pudieron leer los datos de la factura.'
    expect(explanationNotes({ summary: 'Escalada', explanation: unread })).toEqual([
      'No se pudieron leer los datos de la factura.',
    ])
  })

  it('returns nothing when there is no extra explanation', () => {
    expect(explanationNotes({ summary: 'Igual', explanation: 'Igual' })).toEqual([])
    expect(explanationNotes({ summary: 'Solo resumen', explanation: null })).toEqual([])
  })
})
