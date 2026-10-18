import { describe, expect, it } from 'vitest'
import { formatAmount, formatDate, parseTimestamp } from './format'
import { verdictOf } from './status'

describe('formatAmount', () => {
  it('formats decimal strings with grouping and two decimals', () => {
    expect(formatAmount('3400')).toBe('3,400.00')
    expect(formatAmount('8000000.5')).toBe('8,000,000.50')
  })

  it('uses the minor units of the currency', () => {
    expect(formatAmount('300000', 'JPY')).toBe('300,000')
    expect(formatAmount('1200', 'USD')).toBe('1,200.00')
    expect(formatAmount('1200', 'XYZ')).toBe('1,200.00')
  })

  it('returns null when there is no amount', () => {
    expect(formatAmount(null)).toBeNull()
    expect(formatAmount('')).toBeNull()
  })
})

describe('parseTimestamp', () => {
  it('reads timestamps without a zone as UTC', () => {
    expect(parseTimestamp('2026-10-17T03:07:07.636868').toISOString()).toBe('2026-10-17T03:07:07.636Z')
  })

  it('respects an explicit zone', () => {
    expect(parseTimestamp('2026-10-17T03:07:07-05:00').toISOString()).toBe('2026-10-17T08:07:07.000Z')
    expect(parseTimestamp('2026-10-17T03:07:07Z').toISOString()).toBe('2026-10-17T03:07:07.000Z')
  })
})

describe('formatDate', () => {
  it('keeps ISO dates', () => {
    expect(formatDate('2026-10-30')).toBe('2026-10-30')
    expect(formatDate(null)).toBeNull()
  })
})

describe('verdictOf', () => {
  it('names human decisions as approval or rejection', () => {
    expect(verdictOf('pay', 'human')).toBe('Pagada · la aprobó una persona')
    expect(verdictOf('block', 'human')).toBe('Rechazada por una persona')
    expect(verdictOf('escalate', 'agent')).toBe('Por aprobar')
  })
})
