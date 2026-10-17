import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Field, Input, Label, Select, Switch } from '@/components/ui/field'
import { cn } from '@/lib/cn'
import type { FieldSpec, FormValues } from './schemaFields'

export type KeySuggestions = Record<string, { value: string; label: string }[]>

function MapEditor({
  spec,
  rows,
  onChange,
  suggestions,
}: {
  spec: FieldSpec
  rows: [string, string][]
  onChange: (rows: [string, string][]) => void
  suggestions?: { value: string; label: string }[]
}) {
  const listId = `${spec.key}-keys`
  const update = (i: number, part: 0 | 1, value: string) =>
    onChange(rows.map((row, j) => (j === i ? (part === 0 ? [value, row[1]] : [row[0], value]) : row)))

  return (
    <fieldset className="grid gap-2">
      <legend className="text-sm font-medium">{spec.label}</legend>
      {spec.hint ? <p className="-mt-1 text-xs text-ink-muted">{spec.hint}</p> : null}
      {rows.length === 0 ? <p className="text-sm text-ink-muted">Sin entradas.</p> : null}
      {suggestions?.length ? (
        <datalist id={listId}>
          {suggestions.map((s) => (
            <option key={s.value} value={s.value} label={s.label} />
          ))}
        </datalist>
      ) : null}
      {rows.map(([k, v], i) => (
        <div key={i} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-2">
          <Input
            aria-label={`${spec.label}: clave ${i + 1}`}
            value={k}
            list={suggestions?.length ? listId : undefined}
            onChange={(e) => update(i, 0, e.target.value)}
            className="tabular"
          />
          {spec.valueKind === 'enum' && spec.valueOptions ? (
            <Select aria-label={`${spec.label}: valor ${i + 1}`} value={v} onChange={(e) => update(i, 1, e.target.value)}>
              {spec.valueOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          ) : (
            <Input
              aria-label={`${spec.label}: valor ${i + 1}`}
              value={v}
              inputMode={spec.valueKind === 'decimal' ? 'decimal' : undefined}
              onChange={(e) => update(i, 1, e.target.value)}
              className="tabular"
            />
          )}
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Quitar fila ${i + 1} de ${spec.label}`}
            onClick={() => onChange(rows.filter((_, j) => j !== i))}
          >
            <Trash2 />
          </Button>
        </div>
      ))}
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange([...rows, ['', spec.valueOptions?.[0]?.value ?? '']])}
        >
          <Plus />
          Agregar
        </Button>
      </div>
    </fieldset>
  )
}

export function SchemaFields({
  fields,
  values,
  errors,
  onChange,
  idPrefix,
  keySuggestions,
}: {
  fields: FieldSpec[]
  values: FormValues
  errors: Record<string, string>
  onChange: (key: string, value: FormValues[string]) => void
  idPrefix: string
  keySuggestions?: KeySuggestions
}) {
  return (
    <div className="grid gap-5">
      {fields.map((f) => {
        const id = `${idPrefix}-${f.key}`
        const value = values[f.key]
        const error = errors[f.key]
        const describedBy = error ? `${id}-error` : f.hint ? `${id}-hint` : undefined

        if (f.kind === 'map')
          return (
            <MapEditor
              key={f.key}
              spec={f}
              rows={(value as [string, string][]) ?? []}
              onChange={(rows) => onChange(f.key, rows)}
              suggestions={keySuggestions?.[f.key]}
            />
          )

        if (f.kind === 'boolean')
          return (
            <div key={f.key} className="flex items-start justify-between gap-4">
              <div className="space-y-0.5">
                <Label htmlFor={id}>{f.label}</Label>
                {f.hint ? (
                  <p id={`${id}-hint`} className="text-xs text-ink-muted">
                    {f.hint}
                  </p>
                ) : null}
              </div>
              <Switch
                id={id}
                checked={Boolean(value)}
                onCheckedChange={(checked) => onChange(f.key, checked)}
                aria-describedby={f.hint ? `${id}-hint` : undefined}
              />
            </div>
          )

        if (f.kind === 'readonly')
          return (
            <div key={f.key} className="flex items-baseline justify-between gap-4 rounded-lg bg-paper-deep/70 px-3 py-2">
              <span className="text-sm text-ink-soft">{f.label}</span>
              <span className="tabular text-sm font-medium">
                {f.key === 'version' ? `v${String(value)}` : String(value)}
              </span>
            </div>
          )

        return (
          <Field
            key={f.key}
            label={
              <>
                {f.label}
                {(f.required && !f.nullable) || f.hasDefault ? null : (
                  <span className="font-normal text-ink-muted"> (opcional)</span>
                )}
              </>
            }
            htmlFor={id}
            hint={f.hint}
            error={error}
          >
            {f.kind === 'enum' && f.options ? (
              <Select
                id={id}
                value={String(value)}
                onChange={(e) => onChange(f.key, e.target.value)}
                aria-describedby={describedBy}
                aria-invalid={Boolean(error)}
              >
                {f.nullable || !f.required ? (
                  <option value="">—</option>
                ) : (
                  <option value="" disabled>
                    Elige una opción…
                  </option>
                )}
                {f.options.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                id={id}
                type={f.kind === 'date' ? 'date' : 'text'}
                inputMode={
                  f.kind === 'decimal' || f.kind === 'number' ? 'decimal' : f.kind === 'integer' ? 'numeric' : undefined
                }
                value={String(value ?? '')}
                onChange={(e) => onChange(f.key, e.target.value)}
                aria-describedby={describedBy}
                aria-invalid={Boolean(error)}
                className={cn(['decimal', 'number', 'integer', 'date'].includes(f.kind) && 'tabular')}
              />
            )}
          </Field>
        )
      })}
    </div>
  )
}
