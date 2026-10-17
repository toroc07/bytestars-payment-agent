import { describe, expect, it } from 'vitest'
import { kindOf, problemWith, toOutgoing } from './files'

const file = (name: string, type: string, content = 'x') => new File([content], name, { type })

describe('kindOf', () => {
  it('sends PDFs and images as documents', () => {
    expect(kindOf(file('a.pdf', 'application/pdf'))).toBe('document')
    expect(kindOf(file('a.png', 'image/png'))).toBe('document')
    expect(kindOf(file('a.jpg', 'image/jpeg'))).toBe('document')
  })

  it('reads emails and text files as text, by type or by extension', () => {
    expect(kindOf(file('correo.eml', 'message/rfc822'))).toBe('text')
    expect(kindOf(file('nota.txt', 'text/plain'))).toBe('text')
    expect(kindOf(file('correo.eml', ''))).toBe('text')
  })

  it('rejects anything else', () => {
    expect(kindOf(file('hoja.xlsx', 'application/vnd.ms-excel'))).toBeNull()
    expect(problemWith(file('hoja.xlsx', 'application/vnd.ms-excel'))).toMatch(/no se puede leer/)
  })
})

describe('toOutgoing', () => {
  it('keeps documents as files and passes the note as text', async () => {
    const pdf = file('f.pdf', 'application/pdf')
    expect(await toOutgoing(pdf, 'nota')).toEqual({ file: pdf, text: 'nota' })
  })

  it('inlines text files with their name and the note first', async () => {
    const txt = file('chat-01.txt', 'text/plain', '  Total: USD 950.00  ')
    expect(await toOutgoing(txt, 'urgente')).toEqual({
      text: 'urgente\n\nchat-01.txt\n\nTotal: USD 950.00',
    })
  })

  it('opens an email: decoded headers and body as text, the PDF attachment as the file', async () => {
    const raw = [
      'From: =?utf-8?q?Jos=C3=A9?= <cobros@ficticio.example>',
      'Subject: =?utf-8?q?Env=C3=ADo?= factura 7',
      'Content-Type: multipart/mixed; boundary="B"',
      '',
      '--B',
      'Content-Type: text/plain; charset="utf-8"',
      'Content-Transfer-Encoding: quoted-printable',
      '',
      'Adjunto la factura por concepto de cab=',
      'leado. Total =24 950.',
      '--B',
      'Content-Type: application/pdf',
      'Content-Disposition: attachment; filename="factura-7.pdf"',
      'Content-Transfer-Encoding: base64',
      '',
      btoa('%PDF-1.4 fake'),
      '--B--',
    ].join('\r\n')
    const out = await toOutgoing(file('correo-07.eml', 'message/rfc822', raw), undefined)
    expect(out.text).toContain('De: José <cobros@ficticio.example>')
    expect(out.text).toContain('Asunto: Envío factura 7')
    expect(out.text).toContain('por concepto de cableado. Total $ 950.')
    expect(out.file?.name).toBe('factura-7.pdf')
    expect(out.file?.type).toBe('application/pdf')
    expect(await out.file?.text()).toBe('%PDF-1.4 fake')
  })

  it('sends just the note when there is no file', async () => {
    expect(await toOutgoing(undefined, 'hola')).toEqual({ text: 'hola' })
  })
})
