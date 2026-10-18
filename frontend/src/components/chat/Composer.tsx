import { ArrowUp, FileText, ImageIcon, Mail, Paperclip, X } from 'lucide-react'
import { useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'
import { ACCEPT, kindOf, MAX_BATCH, MAX_FILE_MB, problemWith } from '@/lib/files'
import { formatBytes } from '@/lib/format'

export interface ComposerSubmit {
  note?: string
  files: File[]
}

function iconFor(file: File) {
  if (file.type === 'application/pdf') return FileText
  if (kindOf(file) === 'document') return ImageIcon
  return Mail
}

export function Composer({
  onSubmit,
  busy,
  disabled,
  autoFocus,
  multiple = false,
}: {
  onSubmit: (input: ComposerSubmit) => void
  busy: boolean
  disabled?: boolean
  autoFocus?: boolean
  /** Accept several files at once (each becomes its own invoice). */
  multiple?: boolean
}) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [problems, setProblems] = useState<string[]>([])
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const textRef = useRef<HTMLTextAreaElement>(null)

  const canSend = !busy && !disabled && (text.trim() !== '' || files.length > 0)

  function add(list: FileList | File[] | null | undefined) {
    if (!list || list.length === 0) return
    const incoming = Array.from(list)
    const issues = incoming.map(problemWith).filter((p): p is string => p !== null)
    const valid = incoming.filter((f) => problemWith(f) === null)
    let next = multiple ? [...files, ...valid] : valid.slice(0, 1)
    if (multiple && next.length > MAX_BATCH) {
      issues.push(`Se pueden procesar hasta ${MAX_BATCH} archivos por lote; se tomaron los primeros ${MAX_BATCH}.`)
      next = next.slice(0, MAX_BATCH)
    }
    if (!multiple && incoming.length > 1) issues.push('Aquí se procesa un archivo a la vez; se tomó el primero.')
    setProblems(issues)
    setFiles(next)
    textRef.current?.focus()
  }

  function submit(event?: FormEvent) {
    event?.preventDefault()
    if (!canSend) return
    onSubmit({ note: text.trim() || undefined, files })
    setText('')
    setFiles([])
    setProblems([])
    if (inputRef.current) inputRef.current.value = ''
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    add(event.dataTransfer.files)
  }

  const batch = files.length > 1

  return (
    <form
      onSubmit={submit}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={cn(
        'rounded-xl bg-sheet shadow-[inset_0_0_0_1px_var(--color-rule-strong),0_8px_24px_-18px_rgb(30_28_24/0.5)] transition-shadow duration-150 focus-within:shadow-[inset_0_0_0_2px_var(--color-intaglio),0_8px_24px_-18px_rgb(30_28_24/0.5)]',
        dragging && 'bg-intaglio-tint/40 shadow-[inset_0_0_0_2px_var(--color-intaglio)]',
      )}
    >
      {files.length > 0 ? (
        <div className="max-h-36 overflow-y-auto px-3 pt-3">
          <ul className="flex flex-wrap gap-1.5" aria-label="Archivos adjuntos">
            {files.map((file, i) => {
              const Icon = iconFor(file)
              return (
                <li
                  key={`${file.name}-${i}`}
                  className="inline-flex max-w-full items-center gap-2 rounded-lg bg-paper-deep py-1 pr-1 pl-2.5 text-sm"
                >
                  <Icon className="size-4 shrink-0 text-ink-soft" aria-hidden="true" />
                  <span className="max-w-56 truncate">{file.name}</span>
                  <span className="tabular shrink-0 text-xs text-ink-muted">{formatBytes(file.size)}</span>
                  <button
                    type="button"
                    onClick={() => setFiles((list) => list.filter((_, j) => j !== i))}
                    className="pressable grid size-6 shrink-0 place-items-center rounded-md text-ink-muted hover:bg-rule hover:text-ink"
                    aria-label={`Quitar ${file.name}`}
                  >
                    <X className="size-3.5" />
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}

      <label htmlFor="composer-text" className="sr-only">
        Mensaje o texto de la factura
      </label>
      <textarea
        id="composer-text"
        ref={textRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        rows={2}
        autoFocus={autoFocus}
        disabled={disabled}
        placeholder={
          batch
            ? `${files.length} facturas listas. Cada una se revisa por separado.`
            : files.length === 1
              ? 'Agrega una nota (opcional)…'
              : 'Pega una factura, un correo o un mensaje… o pregunta por una decisión'
        }
        aria-describedby={problems.length ? 'composer-error' : 'composer-hint'}
        className="field-sizing-content block max-h-60 min-h-14 w-full resize-none bg-transparent px-4 pt-3 text-[0.9375rem] leading-relaxed text-ink placeholder:text-ink-muted focus:outline-none disabled:opacity-60"
      />

      <div className="flex items-center justify-between gap-3 px-2.5 pb-2.5">
        <div className="flex min-w-0 items-center gap-1">
          <input
            ref={inputRef}
            type="file"
            multiple={multiple}
            accept={ACCEPT}
            className="sr-only"
            id="composer-file"
            tabIndex={-1}
            onChange={(e) => add(e.target.files)}
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => inputRef.current?.click()}
            disabled={disabled || busy}
          >
            <Paperclip />
            {multiple ? 'Adjuntar archivos' : 'Adjuntar archivo'}
          </Button>
          <p id="composer-hint" className="hidden truncate text-xs text-ink-muted lg:block">
            PDF, imagen, correo (.eml) o texto · máx. {MAX_FILE_MB} MB
            {multiple ? ` · hasta ${MAX_BATCH} a la vez` : ''} · Enter envía
          </p>
        </div>
        <Button
          type="submit"
          variant="primary"
          size={batch ? 'md' : 'icon'}
          disabled={!canSend}
          aria-label={batch ? undefined : 'Enviar factura'}
        >
          {batch ? `Revisar ${files.length} facturas` : <ArrowUp />}
        </Button>
      </div>

      {problems.length ? (
        <div id="composer-error" role="alert" className="space-y-1 border-t border-rule px-4 py-2 text-sm text-brick">
          {problems.map((p) => (
            <p key={p}>{p}</p>
          ))}
        </div>
      ) : null}
    </form>
  )
}
