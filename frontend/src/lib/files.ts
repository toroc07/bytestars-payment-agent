import { emailAsText, parseEmail } from './eml'
import { formatBytes } from './format'

/** What the backend reads as a document; everything textual is read here and sent as text. */
export const DOCUMENT_TYPES = ['application/pdf', 'image/png', 'image/jpeg']
// Outlook .msg is binary (not text), so it is deliberately absent.
const TEXT_EXTENSIONS = ['.txt', '.eml', '.md', '.text']
export const ACCEPT = [...DOCUMENT_TYPES, 'text/plain', 'message/rfc822', ...TEXT_EXTENSIONS].join(',')

export const MAX_FILE_MB = 4
export const MAX_BATCH = 50

export type FileKind = 'document' | 'text'

export function kindOf(file: File): FileKind | null {
  if (DOCUMENT_TYPES.includes(file.type)) return 'document'
  const name = file.name.toLowerCase()
  if (file.type.startsWith('text/') || file.type === 'message/rfc822') return 'text'
  if (TEXT_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'text'
  return null
}

/** Returns a user-facing problem with the file, or null when it can be sent. */
export function problemWith(file: File): string | null {
  if (!kindOf(file)) return `«${file.name}» no se puede leer. Usa PDF, PNG, JPG o un correo/texto (.eml, .txt).`
  if (file.size > MAX_FILE_MB * 1024 * 1024)
    return `«${file.name}» pesa ${formatBytes(file.size)}; el máximo es ${MAX_FILE_MB} MB.`
  return null
}

export interface OutgoingMessage {
  text?: string
  file?: File
}

const isEmail = (file: File) => file.type === 'message/rfc822' || file.name.toLowerCase().endsWith('.eml')

/**
 * Documents go as files. Emails are opened here: headers and body become the text, and the first
 * PDF/image attachment goes as the file (the actual invoice). Plain text files go as text.
 */
export async function toOutgoing(file: File | undefined, note: string | undefined): Promise<OutgoingMessage> {
  if (!file) return { text: note }
  if (kindOf(file) === 'document') return { file, text: note }
  const join = (body: string) => (note ? `${note}\n\n${body}` : body)

  const raw = await file.text()
  if (isEmail(file)) {
    const email = parseEmail(raw)
    const attachment = email.attachments[0]
    return { text: join(emailAsText(email, file.name)), file: attachment }
  }
  return { text: join(`${file.name}\n\n${raw.trim()}`) }
}
