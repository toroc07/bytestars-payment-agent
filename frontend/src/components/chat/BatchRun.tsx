import { ArrowRight } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useSendMessage } from '@/api/hooks'
import type { Outcome } from '@/api/types'
import { StatusGlyph } from '@/components/decision/StatusGlyph'
import { Button } from '@/components/ui/button'
import { toOutgoing } from '@/lib/files'
import { OUTCOME } from '@/lib/status'

interface Item {
  file: File
  status: 'queued' | 'running' | 'done' | 'error'
  conversationId?: string
  outcome?: Outcome
  error?: string
}

/** Runs a batch of invoices one after another; each becomes its own conversation. */
export function BatchRun({ files, note, onClose }: { files: File[]; note?: string; onClose: () => void }) {
  const { mutateAsync } = useSendMessage()
  const [items, setItems] = useState<Item[]>(() => files.map((file) => ({ file, status: 'queued' })))
  const [stopped, setStopped] = useState(false)
  const stopRef = useRef(false)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    const update = (i: number, patch: Partial<Item>) =>
      setItems((list) => list.map((item, j) => (j === i ? { ...item, ...patch } : item)))

    void (async () => {
      for (let i = 0; i < files.length; i++) {
        if (stopRef.current) break
        update(i, { status: 'running' })
        try {
          const outgoing = await toOutgoing(files[i], note)
          const { conversationId, result } = await mutateAsync(outgoing)
          update(i, { status: 'done', conversationId, outcome: result.assistant_message.decision?.outcome })
        } catch (error) {
          update(i, { status: 'error', error: error instanceof Error ? error.message : 'Error desconocido' })
        }
      }
    })()
  }, [files, note, mutateAsync])

  const finished = items.filter((i) => i.status === 'done' || i.status === 'error').length
  const running = items.some((i) => i.status === 'running')
  const complete = !running && (finished === items.length || stopped)
  const count = (o: Outcome) => items.filter((i) => i.outcome === o).length
  const errors = items.filter((i) => i.status === 'error').length

  return (
    <section aria-labelledby="batch-title" className="rounded-xl bg-sheet ring-1 ring-rule-strong">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-rule px-5 py-4">
        <div>
          <h2 id="batch-title" className="text-lg font-semibold tracking-tight">
            {complete ? 'Lote revisado' : 'Revisando lote'}
          </h2>
          <p className="mt-1 text-sm text-ink-soft" role="status" aria-live="polite">
            <span className="tabular">
              {finished}/{items.length}
            </span>{' '}
            revisadas · <span className="tabular">{count('pay')}</span> pagadas ·{' '}
            <span className="tabular">{count('escalate')}</span> escaladas ·{' '}
            <span className="tabular">{count('block')}</span> rechazadas
            {errors ? (
              <>
                {' '}
                · <span className="tabular">{errors}</span> con error
              </>
            ) : null}
          </p>
        </div>
        {complete ? (
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cerrar
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/registro">
                Ver registro
                <ArrowRight />
              </Link>
            </Button>
          </div>
        ) : (
          <Button
            variant="secondary"
            disabled={stopped}
            onClick={() => {
              stopRef.current = true
              setStopped(true)
            }}
          >
            {stopped ? 'Deteniendo…' : 'Detener después de esta'}
          </Button>
        )}
      </div>

      <ol className="max-h-[50vh] divide-y divide-rule overflow-y-auto">
        {items.map((item, i) => {
          const meta = item.outcome ? OUTCOME[item.outcome] : null
          return (
            <li
              key={`${item.file.name}-${i}`}
              className="grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-center gap-x-3 px-5 py-2.5 text-sm"
            >
              <span className="tabular text-xs text-ink-muted">{i + 1}</span>
              <span className="min-w-0">
                <span className="block truncate font-medium">{item.file.name}</span>
                {item.error ? <span className="block text-xs text-brick">{item.error}</span> : null}
              </span>
              <span className="flex items-center gap-2 whitespace-nowrap text-ink-soft">
                {item.status === 'queued' ? <span className="text-ink-muted">En cola</span> : null}
                {item.status === 'running' ? <span className="ink-pulse">Revisando…</span> : null}
                {item.status === 'error' ? <span className="text-brick">No se procesó</span> : null}
                {meta ? (
                  <>
                    <StatusGlyph shape={meta.shape} tone={meta.tone} />
                    {meta.verdict}
                  </>
                ) : null}
                {item.conversationId ? (
                  <Link
                    to={`/c/${item.conversationId}`}
                    className="font-medium text-intaglio underline underline-offset-3"
                    aria-label={`Ver la decisión de ${item.file.name}`}
                  >
                    Ver
                  </Link>
                ) : null}
              </span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
