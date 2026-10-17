import { ChevronDown, Pencil, RotateCcw, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { isOffline } from '@/api/client'
import {
  useAgreements,
  useBeneficiaries,
  useDecisions,
  useDeleteBeneficiary,
  useOpenApi,
  useResetDemo,
  useRules,
  useSaveAgreement,
  useSaveBeneficiary,
  useSaveRules,
} from '@/api/hooks'
import type { Agreement, Beneficiary } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, SheetContent } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatAmount } from '@/lib/format'
import { SchemaFields, type KeySuggestions } from './SchemaForm'
import {
  diffPayloads,
  fieldsFrom,
  findSchema,
  groupFields,
  RULE_GROUPS,
  toFormValues,
  toPayload,
  validate,
  type FieldSpec,
  type FormValues,
} from './schemaFields'

function Notice({ tone = 'muted', children }: { tone?: 'muted' | 'error' | 'ok'; children: ReactNode }) {
  const styles = {
    muted: 'bg-paper-deep/70 text-ink-soft',
    error: 'bg-brick-tint text-brick',
    ok: 'bg-intaglio-tint text-intaglio-deep',
  }[tone]
  return (
    <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-lg px-3 py-2 text-sm ${styles}`}>
      {children}
    </p>
  )
}

const NO_KEYS: string[] = []
type EnumOverrides = Record<string, { value: string; label: string }[]>
const NO_OVERRIDES: EnumOverrides = {}

function useSchemaFields(
  names: string[],
  readonlyKeys: string[] = NO_KEYS,
  enumOverrides: EnumOverrides = NO_OVERRIDES,
) {
  const doc = useOpenApi()
  const schema = findSchema(doc.data, ...names)
  const fields = useMemo(() => {
    if (!schema) return []
    return fieldsFrom(schema, readonlyKeys).map((f) =>
      enumOverrides[f.key] ? { ...f, kind: 'enum' as const, options: enumOverrides[f.key] } : f,
    )
  }, [schema, readonlyKeys, enumOverrides])
  return { doc, fields }
}

/* ---------- Reglas ---------- */

const RULE_READONLY = ['version']

function RulesTab({ resetKey, onDirtyChange }: { resetKey: number; onDirtyChange: (dirty: boolean) => void }) {
  const rules = useRules()
  const { doc, fields } = useSchemaFields(['RuleSet-Input', 'RuleSet'], RULE_READONLY)
  const decisions = useDecisions()
  // Lives here, not in the form, so the "saved" notice survives the remount below.
  const save = useSaveRules()

  // Rule ids the engine has actually reported, offered as keys for severity overrides.
  const keySuggestions = useMemo<KeySuggestions>(() => {
    const seen = new Map<string, string>()
    for (const d of decisions.data ?? []) for (const c of d.checks) seen.set(c.rule_id, c.rule_name)
    return { severity_overrides: [...seen].sort().map(([value, label]) => ({ value, label })) }
  }, [decisions.data])

  if (rules.isPending || doc.isPending) return <Notice>Cargando reglas…</Notice>
  if (rules.isError)
    return (
      <Notice tone={isOffline(rules.error) ? 'muted' : 'error'}>
        {isOffline(rules.error)
          ? 'Sin conexión con el servidor. Las reglas se mostrarán cuando vuelva.'
          : 'Las reglas de la empresa aún no están cargadas en el servidor.'}
      </Notice>
    )
  if (!fields.length)
    return <Notice>El servidor no publica todavía la estructura de las reglas, así que no hay nada que editar.</Notice>

  // Remount on every new version (or a discard) so the form starts from what the server holds.
  return (
    <RulesForm
      key={`${rules.data.version}-${resetKey}`}
      fields={fields}
      rules={rules.data as Record<string, unknown>}
      save={save}
      keySuggestions={keySuggestions}
      onDirtyChange={onDirtyChange}
    />
  )
}

function RulesForm({
  fields,
  rules,
  save,
  keySuggestions,
  onDirtyChange,
}: {
  fields: FieldSpec[]
  rules: Record<string, unknown>
  save: ReturnType<typeof useSaveRules>
  keySuggestions: KeySuggestions
  onDirtyChange: (dirty: boolean) => void
}) {
  const initial = useMemo(() => toFormValues(fields, rules), [fields, rules])
  const baseline = useMemo(() => toPayload(fields, initial, rules), [fields, initial, rules])
  const [values, setValues] = useState<FormValues>(initial)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const groups = useMemo(() => groupFields(fields, RULE_GROUPS), [fields])
  const changes = diffPayloads(fields, baseline, toPayload(fields, values, rules))
  const dirty = changes.length > 0

  function change(key: string, value: FormValues[string]) {
    const next = { ...values, [key]: value }
    setValues(next)
    if (save.isSuccess) save.reset()
    onDirtyChange(diffPayloads(fields, baseline, toPayload(fields, next, rules)).length > 0)
  }

  function discard() {
    setErrors({})
    save.reset()
    setValues(initial)
    onDirtyChange(false)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const found = validate(fields, values)
    setErrors(found)
    if (Object.keys(found).length || !dirty) return
    save.mutate(toPayload(fields, values, rules), { onSuccess: () => onDirtyChange(false) })
  }

  return (
    <form onSubmit={submit} className="grid gap-6" noValidate>
      <p className="text-sm leading-relaxed text-ink-soft">
        El motor aplica estas reglas a cada factura. Si una no se cumple, la factura se rechaza o se escala; nunca se
        paga. Guardar crea una versión nueva: las decisiones anteriores conservan la versión con la que se tomaron.
      </p>

      {groups.map(({ group, fields: members }) => {
        const body = (
          <SchemaFields
            idPrefix="rules"
            fields={members}
            values={values}
            errors={errors}
            onChange={change}
            keySuggestions={keySuggestions}
          />
        )
        const hasError = members.some((f) => errors[f.key])
        return group.collapsed ? (
          <details key={group.title} open={hasError || undefined} className="group rounded-xl bg-sheet ring-1 ring-rule">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold">
              {group.title}
              <ChevronDown
                className="size-4 text-ink-muted transition-transform duration-200 group-open:rotate-180"
                aria-hidden="true"
              />
            </summary>
            <div className="border-t border-rule px-4 py-4">{body}</div>
          </details>
        ) : (
          <fieldset key={group.title} className="grid gap-4">
            <legend className="mb-1 text-sm font-semibold">{group.title}</legend>
            {group.hint ? <p className="-mt-2 text-xs text-ink-muted">{group.hint}</p> : null}
            {body}
          </fieldset>
        )
      })}

      {save.isError ? <Notice tone="error">No se pudo guardar: {save.error.message}</Notice> : null}
      {save.isSuccess && !dirty ? (
        <Notice tone="ok">Guardado. Ahora rige la versión v{save.data.version}.</Notice>
      ) : null}

      {dirty || save.isPending ? (
      <div className="sticky bottom-0 -mx-6 grid gap-3 border-t border-rule bg-paper px-6 py-4">
        {dirty ? (
          <div aria-live="polite">
            <p className="text-sm font-semibold">
              {changes.length === 1 ? '1 cambio sin guardar' : `${changes.length} cambios sin guardar`}
            </p>
            <ul className="mt-1 max-h-28 space-y-0.5 overflow-y-auto text-sm text-ink-soft">
              {changes.map((c) => (
                <li key={c.key} className="min-w-0 break-words">
                  {c.label}: <span className="tabular text-ink-muted line-through">{c.before}</span> →{' '}
                  <span className="tabular font-medium text-ink">{c.after}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="ghost" onClick={discard} disabled={!dirty}>
            Descartar cambios
          </Button>
          <Button type="submit" variant="primary" disabled={!dirty || save.isPending}>
            {save.isPending ? 'Guardando…' : `Guardar como versión v${Number(rules.version ?? 0) + 1}`}
          </Button>
        </div>
      </div>
      ) : null}
    </form>
  )
}

/* ---------- Formularios de alta y edición ---------- */

function RecordForm({
  fields,
  idPrefix,
  initial,
  submitLabel,
  onSave,
  onCancel,
  pending,
  error,
}: {
  fields: FieldSpec[]
  idPrefix: string
  initial: Record<string, unknown>
  submitLabel: string
  onSave: (payload: Record<string, unknown>) => void
  onCancel?: () => void
  pending: boolean
  error: Error | null
}) {
  const [values, setValues] = useState<FormValues>(() => toFormValues(fields, initial))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const ref = useRef<HTMLFormElement>(null)
  const editing = Boolean(onCancel)

  // Editing opens the form below the list: bring it into view.
  useEffect(() => {
    if (editing) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [editing])

  function submit(event: FormEvent) {
    event.preventDefault()
    const found = validate(fields, values)
    setErrors(found)
    if (Object.keys(found).length) return
    onSave(toPayload(fields, values, initial))
  }

  return (
    <form ref={ref} onSubmit={submit} noValidate className="grid gap-5 rounded-xl bg-sheet p-5 ring-1 ring-rule">
      <SchemaFields
        idPrefix={idPrefix}
        fields={fields}
        values={values}
        errors={errors}
        onChange={(key, value) => setValues((v) => ({ ...v, [key]: value }))}
      />
      {error ? <Notice tone="error">{error.message}</Notice> : null}
      <div className="flex justify-end gap-2">
        {onCancel ? (
          <Button variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        ) : null}
        <Button type="submit" variant="primary" disabled={pending}>
          {pending ? 'Guardando…' : submitLabel}
        </Button>
      </div>
    </form>
  )
}

const ID_READONLY = ['id']

function RowActions({
  name,
  onEdit,
  onDelete,
  deleting,
}: {
  name: string
  onEdit: () => void
  onDelete?: () => void
  deleting?: boolean
}) {
  const [confirming, setConfirming] = useState(false)
  if (confirming && onDelete)
    return (
      <div className="flex items-center gap-1" role="group" aria-label={`Confirmar quitar a ${name}`}>
        <span className="mr-1 text-xs text-ink-soft">¿Quitar?</span>
        <Button variant="danger" size="sm" disabled={deleting} onClick={onDelete}>
          Quitar
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
          No
        </Button>
      </div>
    )
  return (
    <div className="flex items-center">
      <Button variant="ghost" size="icon" aria-label={`Editar ${name}`} onClick={onEdit}>
        <Pencil />
      </Button>
      {onDelete ? (
        <Button variant="ghost" size="icon" aria-label={`Quitar a ${name} de la lista`} onClick={() => setConfirming(true)}>
          <Trash2 />
        </Button>
      ) : null}
    </div>
  )
}

/* ---------- Beneficiarios ---------- */

// Verification is a human step (rule R04): a new vendor starts unverified and not sanctioned.
const NEW_BENEFICIARY = { verified: false, sanctioned: false, allowed: true }

function BeneficiariesTab() {
  const list = useBeneficiaries()
  const save = useSaveBeneficiary()
  const remove = useDeleteBeneficiary()
  const [editing, setEditing] = useState<Beneficiary | null>(null)
  const [savedName, setSavedName] = useState<string | null>(null)
  const { fields: createFields } = useSchemaFields(['Beneficiary'])
  const { fields: editFields } = useSchemaFields(['Beneficiary'], ID_READONLY)

  function persist(payload: Record<string, unknown>) {
    save.mutate(payload, {
      onSuccess: (b) => {
        setSavedName(b.name)
        setEditing(null)
      },
    })
  }

  return (
    <div className="grid gap-6">
      <p className="text-sm leading-relaxed text-ink-soft">
        Solo se paga sin intervención a quienes están en esta lista. Un beneficiario nuevo se escala a una persona.
      </p>
      {list.isPending ? (
        <Notice>Cargando beneficiarios…</Notice>
      ) : list.isError ? (
        <Notice tone="error">{list.error.message}</Notice>
      ) : list.data.length === 0 ? (
        <Notice>Todavía no hay beneficiarios permitidos.</Notice>
      ) : (
        <ul className="divide-y divide-rule rounded-xl bg-sheet ring-1 ring-rule">
          {list.data.map((b) => (
            <li key={b.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">
                  {b.name}
                  {b.allowed === false ? <span className="font-normal text-brick"> · no permitido</span> : null}
                </p>
                <p className="tabular truncate text-xs text-ink-muted">
                  {[b.country, b.tax_id, b.account].filter(Boolean).join(' · ') || b.id}
                </p>
              </div>
              <RowActions
                name={b.name}
                onEdit={() => {
                  save.reset()
                  setSavedName(null)
                  setEditing(b)
                }}
                onDelete={() => remove.mutate(b.id)}
                deleting={remove.isPending}
              />
            </li>
          ))}
        </ul>
      )}
      {remove.isError ? <Notice tone="error">{remove.error.message}</Notice> : null}
      {savedName ? <Notice tone="ok">{savedName} quedó guardado.</Notice> : null}

      {createFields.length ? (
        <div className="grid gap-3">
          <h3 className="text-sm font-semibold">{editing ? `Editar ${editing.name}` : 'Agregar beneficiario'}</h3>
          {editing ? (
            <RecordForm
              key={`edit-${editing.id}`}
              idPrefix="beneficiary-edit"
              fields={editFields}
              initial={editing as unknown as Record<string, unknown>}
              submitLabel="Guardar cambios"
              onSave={persist}
              onCancel={() => setEditing(null)}
              pending={save.isPending}
              error={save.error}
            />
          ) : (
            <RecordForm
              key={`new-${savedName ?? ''}`}
              idPrefix="beneficiary"
              fields={createFields}
              initial={NEW_BENEFICIARY}
              submitLabel="Agregar a la lista"
              onSave={persist}
              pending={save.isPending}
              error={save.error}
            />
          )}
        </div>
      ) : null}
    </div>
  )
}

/* ---------- Acuerdos ---------- */

function AgreementsTab() {
  const list = useAgreements()
  const beneficiaries = useBeneficiaries()
  const save = useSaveAgreement()
  const [editing, setEditing] = useState<Agreement | null>(null)
  const [saved, setSaved] = useState(0)
  const nameOf = (id: string) => beneficiaries.data?.find((b) => b.id === id)?.name ?? id

  const overrides = useMemo<EnumOverrides>(
    () => ({
      beneficiary_id: (beneficiaries.data ?? []).map((b) => ({ value: b.id, label: b.name })),
    }),
    [beneficiaries.data],
  )
  const { fields: createFields } = useSchemaFields(['Agreement-Input', 'Agreement'], NO_KEYS, overrides)
  const { fields: editFields } = useSchemaFields(['Agreement-Input', 'Agreement'], ID_READONLY, overrides)

  function persist(payload: Record<string, unknown>) {
    save.mutate(payload, {
      onSuccess: () => {
        setSaved((n) => n + 1)
        setEditing(null)
      },
    })
  }

  return (
    <div className="grid gap-6">
      <p className="text-sm leading-relaxed text-ink-soft">
        Lo acordado con cada beneficiario. Una factura que no cuadra con su acuerdo no se paga.
      </p>
      {list.isPending ? (
        <Notice>Cargando acuerdos…</Notice>
      ) : list.isError ? (
        <Notice tone="error">{list.error.message}</Notice>
      ) : list.data.length === 0 ? (
        <Notice>Todavía no hay acuerdos registrados.</Notice>
      ) : (
        <ul className="divide-y divide-rule rounded-xl bg-sheet ring-1 ring-rule">
          {list.data.map((a) => (
            <li key={a.id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-x-3 px-4 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{nameOf(a.beneficiary_id)}</p>
                <p className="truncate text-xs text-ink-muted">
                  {a.description}
                  {a.po_reference ? <span className="tabular"> · {a.po_reference}</span> : null}
                </p>
              </div>
              <p className="tabular text-sm">
                <span className="text-ink-muted">{a.currency}</span> {formatAmount(a.expected_amount, a.currency)}
              </p>
              <RowActions
                name={`el acuerdo de ${nameOf(a.beneficiary_id)}`}
                onEdit={() => {
                  save.reset()
                  setEditing(a)
                }}
              />
            </li>
          ))}
        </ul>
      )}
      {saved > 0 && !editing ? <Notice tone="ok">Acuerdo guardado.</Notice> : null}

      {createFields.length ? (
        <div className="grid gap-3">
          <h3 className="text-sm font-semibold">
            {editing ? `Editar acuerdo de ${nameOf(editing.beneficiary_id)}` : 'Registrar acuerdo'}
          </h3>
          {beneficiaries.data?.length === 0 ? (
            <Notice>Primero agrega un beneficiario: cada acuerdo pertenece a uno.</Notice>
          ) : editing ? (
            <RecordForm
              key={`edit-${editing.id}`}
              idPrefix="agreement-edit"
              fields={editFields}
              initial={editing as unknown as Record<string, unknown>}
              submitLabel="Guardar cambios"
              onSave={persist}
              onCancel={() => setEditing(null)}
              pending={save.isPending}
              error={save.error}
            />
          ) : (
            <RecordForm
              key={`new-${saved}`}
              idPrefix="agreement"
              fields={createFields}
              initial={{}}
              submitLabel="Guardar acuerdo"
              onSave={persist}
              pending={save.isPending}
              error={save.error}
            />
          )}
        </div>
      ) : null}
    </div>
  )
}

/* ---------- Demo ---------- */

function DemoTab({ onDone }: { onDone: () => void }) {
  const reset = useResetDemo()
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)

  return (
    <div className="grid gap-5">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Reiniciar la demo</h3>
        <p className="text-sm leading-relaxed text-ink-soft">
          Borra todas las facturas, decisiones y conversaciones, y vuelve a cargar la empresa del dataset (reglas,
          beneficiarios y acuerdos). Úsalo para empezar una demostración desde cero.
        </p>
      </div>
      {reset.isError ? <Notice tone="error">{reset.error.message}</Notice> : null}
      {confirming ? (
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-brick-tint/60 p-4 ring-1 ring-brick-rule">
          <p className="mr-auto text-sm text-brick">Esto no se puede deshacer.</p>
          <Button variant="ghost" onClick={() => setConfirming(false)}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            disabled={reset.isPending}
            onClick={() =>
              reset.mutate(undefined, {
                onSuccess: () => {
                  setConfirming(false)
                  onDone()
                  navigate('/')
                },
              })
            }
          >
            {reset.isPending ? 'Reiniciando…' : 'Sí, borrar todo y reiniciar'}
          </Button>
        </div>
      ) : (
        <div>
          <Button variant="danger" onClick={() => setConfirming(true)}>
            <RotateCcw />
            Reiniciar demo
          </Button>
        </div>
      )}
    </div>
  )
}

export function SettingsSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [rulesDirty, setRulesDirty] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)
  const [resetKey, setResetKey] = useState(0)

  function requestClose(next: boolean) {
    if (!next && rulesDirty) {
      setConfirmClose(true)
      return
    }
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={requestClose}>
      <SheetContent
        title="Configuración"
        description="Las reglas con las que el agente decide, a quién puede pagar y lo acordado con cada uno."
      >
        <Tabs defaultValue="rules" className="px-6 pt-5 pb-6">
          <TabsList aria-label="Secciones de configuración" className="grid w-full grid-cols-4 sm:inline-flex sm:w-auto">
            <TabsTrigger value="rules" className="justify-center px-1.5 text-xs sm:px-3 sm:text-sm">
              Reglas
              {rulesDirty ? (
                <span className="size-1.5 rounded-full bg-ochre" role="img" aria-label="cambios sin guardar" />
              ) : null}
            </TabsTrigger>
            <TabsTrigger value="beneficiaries" className="justify-center px-1.5 text-xs sm:px-3 sm:text-sm">
              Beneficiarios
            </TabsTrigger>
            <TabsTrigger value="agreements" className="justify-center px-1.5 text-xs sm:px-3 sm:text-sm">
              Acuerdos
            </TabsTrigger>
            <TabsTrigger value="demo" className="justify-center px-1.5 text-xs sm:px-3 sm:text-sm">
              Demo
            </TabsTrigger>
          </TabsList>
          {/* Kept mounted so unsaved rule edits survive switching tabs. */}
          <TabsContent value="rules" forceMount className="pt-6 data-[state=inactive]:hidden">
            <RulesTab resetKey={resetKey} onDirtyChange={setRulesDirty} />
          </TabsContent>
          <TabsContent value="beneficiaries" className="pt-6">
            <BeneficiariesTab />
          </TabsContent>
          <TabsContent value="agreements" className="pt-6">
            <AgreementsTab />
          </TabsContent>
          <TabsContent value="demo" className="pt-6">
            <DemoTab onDone={() => onOpenChange(false)} />
          </TabsContent>
        </Tabs>
      </SheetContent>

      <Dialog open={confirmClose} onOpenChange={setConfirmClose}>
        <DialogContent
          title="Tienes cambios sin guardar"
          description="Los cambios en las reglas se perderán si cierras ahora."
        >
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmClose(false)}>
              Seguir editando
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                setRulesDirty(false)
                setResetKey((k) => k + 1)
                setConfirmClose(false)
                onOpenChange(false)
              }}
            >
              Descartar y cerrar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Dialog>
  )
}
