import { useId } from 'react'

/** Security-print rosette behind the amount: fine interfering sine bands, authored as SVG. */
export function Guilloche({ className }: { className?: string }) {
  const id = useId()
  const width = 640
  const height = 160
  const bands = 9

  const paths = Array.from({ length: bands }, (_, i) => {
    const amplitude = 18 + i * 3.2
    const frequency = 0.018 + i * 0.0011
    const phase = i * 0.7
    const baseline = height / 2 + Math.sin(i) * 6
    let d = ''
    for (let x = 0; x <= width; x += 4) {
      const y =
        baseline +
        Math.sin(x * frequency + phase) * amplitude * Math.cos(x * 0.004 + i * 0.3)
      d += `${x === 0 ? 'M' : 'L'}${x},${y.toFixed(1)}`
    }
    return d
  })

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient id={`${id}-fade`} x1="0" x2="1">
          <stop offset="0" stopColor="var(--color-intaglio)" stopOpacity="0" />
          <stop offset="0.35" stopColor="var(--color-intaglio)" stopOpacity="0.16" />
          <stop offset="1" stopColor="var(--color-intaglio)" stopOpacity="0.1" />
        </linearGradient>
      </defs>
      {paths.map((d, i) => (
        <path key={i} d={d} fill="none" stroke={`url(#${id}-fade)`} strokeWidth="0.8" />
      ))}
    </svg>
  )
}
