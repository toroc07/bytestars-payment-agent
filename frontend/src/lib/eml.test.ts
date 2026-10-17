import { describe, expect, it } from 'vitest'
import { decodeHeader, parseEmail } from './eml'

// The real emails Dev C committed to the dataset (read as raw text through Vite).
const dataset = import.meta.glob('../../../dataset/Correos/*.eml', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

describe('decodeHeader', () => {
  it('decodes RFC 2047 quoted-printable and base64 words', () => {
    expect(decodeHeader('=?utf-8?q?Env=C3=ADo?= factura')).toBe('Envío factura')
    expect(decodeHeader(`=?utf-8?b?${btoa('Cobro')}?= de octubre`)).toBe('Cobro de octubre')
    expect(decodeHeader('Plain subject')).toBe('Plain subject')
  })
})

describe('parseEmail on the dataset', () => {
  const entries = Object.entries(dataset)

  it('finds the 25 dataset emails', () => {
    expect(entries.length).toBe(25)
  })

  it.each(entries.map(([path, raw]) => [path.split('/').pop()!, raw]))(
    '%s: readable sender, subject and body, plus its invoice attachment',
    async (_name, raw) => {
      const email = parseEmail(raw)
      expect(email.from).toBeTruthy()
      expect(email.subject).toBeTruthy()
      expect(email.subject).not.toMatch(/=\?utf-8\?/i)
      expect(email.text.length).toBeGreaterThan(20)
      expect(email.text).not.toMatch(/=\n|=[0-9A-F]{2}/)
      expect(email.attachments.length).toBeGreaterThanOrEqual(1)
      const pdf = email.attachments[0]
      expect(pdf.type).toBe('application/pdf')
      expect((await pdf.text()).startsWith('%PDF')).toBe(true)
    },
  )
})
