import type { StatusShape, StatusTone } from '@/lib/status'
import { cn } from '@/lib/cn'

const toneColor: Record<StatusTone, string> = {
  intaglio: 'var(--color-intaglio)',
  ochre: 'var(--color-ochre)',
  brick: 'var(--color-brick)',
  muted: 'var(--color-ink-muted)',
}

/** State is carried by shape first (disc, ring, square), colour second. Decorative: pair with a text label. */
export function StatusGlyph({
  shape,
  tone,
  className,
}: {
  shape: StatusShape
  tone: StatusTone
  className?: string
}) {
  const color = toneColor[tone]
  return (
    <svg viewBox="0 0 14 14" aria-hidden="true" className={cn('size-3.5 shrink-0', className)}>
      {shape === 'disc' && <circle cx="7" cy="7" r="5.5" fill={color} />}
      {shape === 'ring' && <circle cx="7" cy="7" r="4.75" fill="none" stroke={color} strokeWidth="2.5" />}
      {shape === 'square' && <rect x="2" y="2" width="10" height="10" rx="1.5" fill={color} />}
      {shape === 'dotted' && (
        <circle cx="7" cy="7" r="5" fill="none" stroke={color} strokeWidth="1.5" strokeDasharray="2 2" />
      )}
    </svg>
  )
}
