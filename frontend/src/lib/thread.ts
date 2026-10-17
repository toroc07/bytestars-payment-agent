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
