import type { Decision } from '@/api/types'

export interface ThreadEntry {
  /** An agent decision: rendered as a cheque. */
  decision: Decision
  /** The human decision that resolved it, if any: rendered as the cheque's endorsement. */
  endorsement: Decision | null
}

/**
 * Decisions are append-only. Starting at the decision a chat message carries, every later agent
 * decision (a re-evaluation) becomes a new cheque, and a human decision endorses the cheque before it.
 */
export function buildThread(start: Decision, history: Decision[] | undefined): ThreadEntry[] {
  const later = (history ?? [])
    .filter((d) => d.id !== start.id && d.created_at >= start.created_at)
    .sort((a, b) => a.created_at.localeCompare(b.created_at))

  const thread: ThreadEntry[] = [{ decision: start, endorsement: null }]
  for (const d of later) {
    const last = thread[thread.length - 1]
    if (d.actor === 'human') {
      if (!last.endorsement) last.endorsement = d
    } else {
      thread.push({ decision: d, endorsement: null })
    }
  }
  return thread
}

/**
 * The agent's explanation comes one statement per line. The cheque already shows the verdict (which a
 * person's endorsement can change later), every rule and the "simulated payment" notice, so the only
 * line kept is how the invoice was read: by Gemini, the offline reader, a stored reading, or not at all.
 */
export function explanationNotes(decision: Pick<Decision, 'summary' | 'explanation'>): string[] {
  if (!decision.explanation || decision.explanation === decision.summary) return []
  return decision.explanation
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('Datos leídos con') || line.startsWith('No se pudieron leer'))
}
