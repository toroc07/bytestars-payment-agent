/**
 * Minimal RFC 5322 / MIME reader for .eml invoices: decoded headers, the plain-text body and any
 * PDF or image attachment. Enough for invoice emails; not a general-purpose mail parser.
 */

export interface ParsedEmail {
  from: string | null
  to: string | null
  subject: string | null
  date: string | null
  text: string
  attachments: File[]
}

interface Part {
  headers: Record<string, string>
  body: string
}

const ATTACHMENT_TYPES = ['application/pdf', 'image/png', 'image/jpeg']

function splitHeaders(raw: string): Part {
  const normalized = raw.replace(/\r\n/g, '\n')
  const end = normalized.indexOf('\n\n')
  const head = end === -1 ? normalized : normalized.slice(0, end)
  const body = end === -1 ? '' : normalized.slice(end + 2)
  const headers: Record<string, string> = {}
  // Unfold continuation lines, then read "Name: value".
  for (const line of head.replace(/\n[ \t]+/g, ' ').split('\n')) {
    const i = line.indexOf(':')
    if (i > 0) headers[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim()
  }
  return { headers, body }
}

function param(header: string | undefined, name: string): string | null {
  if (!header) return null
  const match = header.match(new RegExp(`${name}\\*?=(?:"([^"]*)"|([^;\\s]*))`, 'i'))
  return match ? (match[1] ?? match[2] ?? null) : null
}

function bytesToText(bytes: Uint8Array, charset = 'utf-8'): string {
  try {
    return new TextDecoder(charset).decode(bytes)
  } catch {
    return new TextDecoder('utf-8').decode(bytes)
  }
}

function base64ToBytes(input: string): Uint8Array {
  const binary = atob(input.replace(/[^A-Za-z0-9+/=]/g, ''))
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

const encoder = new TextEncoder()

function quotedPrintableToBytes(input: string, header = false): Uint8Array {
  const source = (header ? input.replace(/_/g, ' ') : input).replace(/=\n/g, '')
  const bytes: number[] = []
  for (let i = 0; i < source.length; i++) {
    const hex = source.slice(i + 1, i + 3)
    if (source[i] === '=' && /^[0-9A-Fa-f]{2}$/.test(hex)) {
      bytes.push(Number.parseInt(hex, 16))
      i += 2
    } else {
      bytes.push(...encoder.encode(source[i]))
    }
  }
  return new Uint8Array(bytes)
}

/** RFC 2047 encoded words: =?charset?Q|B?text?= */
export function decodeHeader(value: string | undefined | null): string | null {
  if (!value) return null
  return value
    .replace(/\?=\s+=\?/g, '?==?')
    .replace(/=\?([^?]+)\?([QqBb])\?([^?]*)\?=/g, (_, charset: string, enc: string, text: string) =>
      bytesToText(enc.toUpperCase() === 'B' ? base64ToBytes(text) : quotedPrintableToBytes(text, true), charset),
    )
}

function decodeBody(part: Part): Uint8Array {
  const encoding = (part.headers['content-transfer-encoding'] ?? '7bit').toLowerCase()
  if (encoding === 'base64') return base64ToBytes(part.body)
  if (encoding === 'quoted-printable') return quotedPrintableToBytes(part.body)
  return encoder.encode(part.body)
}

function collect(part: Part, out: { text: string[]; attachments: File[] }) {
  const type = part.headers['content-type'] ?? 'text/plain'
  const rawMime = type.split(';')[0].trim().toLowerCase()
  const mime = rawMime === 'image/jpg' ? 'image/jpeg' : rawMime

  if (mime.startsWith('multipart/')) {
    const boundary = param(type, 'boundary')
    if (!boundary) return
    const sections = part.body.split(`--${boundary}`)
    for (const section of sections.slice(1)) {
      if (section.startsWith('--')) break
      collect(splitHeaders(section.replace(/^\n/, '')), out)
    }
    return
  }

  const disposition = part.headers['content-disposition'] ?? ''
  if (ATTACHMENT_TYPES.includes(mime)) {
    const filename =
      decodeHeader(param(disposition, 'filename') ?? param(type, 'name')) ?? `adjunto.${mime.split('/')[1]}`
    const bytes = decodeBody(part)
    out.attachments.push(new File([new Uint8Array(bytes)], filename, { type: mime }))
    return
  }
  if (mime === 'text/plain' && !/attachment/i.test(disposition)) {
    out.text.push(bytesToText(decodeBody(part), param(type, 'charset') ?? 'utf-8').trim())
  }
}

export function parseEmail(raw: string): ParsedEmail {
  const root = splitHeaders(raw)
  const out = { text: [] as string[], attachments: [] as File[] }
  collect(root, out)
  return {
    from: decodeHeader(root.headers.from),
    to: decodeHeader(root.headers.to),
    subject: decodeHeader(root.headers.subject),
    date: root.headers.date ?? null,
    text: out.text.join('\n\n').trim(),
    attachments: out.attachments,
  }
}

/** The message the agent reads: who sent it, about what, and the body. */
export function emailAsText(email: ParsedEmail, fileName: string): string {
  const lines = [
    `Correo: ${fileName}`,
    email.from ? `De: ${email.from}` : null,
    email.to ? `Para: ${email.to}` : null,
    email.date ? `Fecha: ${email.date}` : null,
    email.subject ? `Asunto: ${email.subject}` : null,
    email.attachments.length > 1
      ? `Adjuntos: ${email.attachments.map((a) => a.name).join(', ')} (se envía el primero)`
      : null,
  ].filter(Boolean)
  return `${lines.join('\n')}\n\n${email.text}`.trim()
}
