// Display-only formatting. The UI never computes decisions from these values.

const formatters = new Map<number, Intl.NumberFormat>()

function formatterFor(digits: number) {
  let f = formatters.get(digits)
  if (!f) {
    f = new Intl.NumberFormat('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    formatters.set(digits, f)
  }
  return f
}

/** Minor units of an ISO 4217 currency (JPY 0, USD 2...), from the browser's own currency data. */
export function currencyDigits(currency: string | null | undefined): number {
  if (!currency) return 2
  try {
    return (
      new Intl.NumberFormat('en-US', { style: 'currency', currency }).resolvedOptions().maximumFractionDigits ?? 2
    )
  } catch {
    return 2
  }
}

export function formatAmount(value: string | number | null | undefined, currency?: string | null): string | null {
  if (value === null || value === undefined || value === '') return null
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n)) return String(value)
  return formatterFor(currencyDigits(currency)).format(n)
}

export function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null
  return iso.slice(0, 10)
}

const timeFormat = new Intl.DateTimeFormat('es', { hour: '2-digit', minute: '2-digit' })
const dayTimeFormat = new Intl.DateTimeFormat('es', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})

/** The API stores UTC but may omit the offset (SQLite drops it); read naive timestamps as UTC. */
export function parseTimestamp(iso: string): Date {
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso)
  return new Date(hasZone || iso.length <= 10 ? iso : `${iso}Z`)
}

export function formatTimestamp(iso: string | null | undefined): string | null {
  if (!iso) return null
  const d = parseTimestamp(iso)
  if (Number.isNaN(d.getTime())) return iso
  const today = new Date()
  const sameDay = d.toDateString() === today.toDateString()
  return sameDay ? timeFormat.format(d) : dayTimeFormat.format(d)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
