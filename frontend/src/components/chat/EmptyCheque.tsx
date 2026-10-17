import { Guilloche } from '@/components/decision/Guilloche'

const STEPS = [
  { title: 'Lee la factura', body: 'Extrae beneficiario, monto, moneda y vencimiento de un PDF, una imagen o un texto.' },
  { title: 'Aplica tus reglas', body: 'Un motor de reglas fijo decide: pagar, rechazar o pedir tu aprobación.' },
  { title: 'Explica cada paso', body: 'Cada regla queda en el talón con lo observado y lo esperado.' },
]

/** First-run state: a blank cheque waiting for its first invoice. */
export function EmptyCheque() {
  return (
    <section aria-labelledby="empty-title" className="w-full">
      <div className="relative grid overflow-hidden rounded-xl bg-sheet/70 ring-1 ring-rule-strong md:grid-cols-[minmax(0,1fr)_17rem]">
        <div className="relative isolate px-6 pt-6 pb-8 sm:px-8 sm:pt-8">
          <Guilloche className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-28 w-full opacity-70" />
          <h1 id="empty-title" className="max-w-[22ch] text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
            Sube una factura y el agente decide si pagarla.
          </h1>
          <p className="mt-3 max-w-[52ch] text-[0.9375rem] leading-relaxed text-ink-soft">
            Responde con un cheque: el veredicto y el monto al frente, y el porqué de cada regla en el talón.
            Los pagos son simulados; no se mueve dinero.
          </p>
          <div className="mt-6 flex items-baseline gap-2 text-ink-muted" aria-hidden="true">
            <span className="tabular text-lg">USD</span>
            <span className="tabular text-4xl font-medium tracking-tight">0.00</span>
          </div>
        </div>
        <ol className="space-y-4 border-t-2 border-dashed border-rule-strong bg-paper/60 px-6 py-6 md:border-t-0 md:border-l-2">
          {STEPS.map((step, i) => (
            <li key={step.title} className="grid grid-cols-[1.5rem_1fr] gap-x-2">
              <span className="tabular text-sm text-ink-muted">{i + 1}</span>
              <div>
                <p className="text-sm font-medium">{step.title}</p>
                <p className="mt-0.5 text-sm leading-snug text-ink-muted">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
