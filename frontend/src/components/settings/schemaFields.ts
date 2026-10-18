import type { JsonSchema, OpenApiDocument } from '@/api/hooks'

/**
 * Turns a JSON Schema object (from the backend's /openapi.json) into form fields.
 * Fields follow whatever the backend declares; the Spanish copy below is only a
 * presentation layer with a fallback for fields it does not know yet.
 */

export type FieldKind =
  | 'text'
  | 'date'
  | 'integer'
  | 'number'
  | 'decimal'
  | 'boolean'
  | 'enum'
  | 'list'
  | 'map'
  | 'readonly'

export interface FieldSpec {
  key: string
  kind: FieldKind
  label: string
  hint?: string
  required: boolean
  nullable: boolean
  /** The backend fills it when omitted, so it is not "optional" from the operator's point of view. */
  hasDefault: boolean
  /** The backend's declared default, used to start a new record. */
  defaultValue?: unknown
  options?: { value: string; label: string }[]
  min?: number
  max?: number
  maxLength?: number
  valueKind?: FieldKind
  valueOptions?: { value: string; label: string }[]
}

/** Invoice data fields the engine can require, as people call them. Keys are what the backend stores. */
export const INVOICE_FIELD_NAMES: Record<string, string> = {
  vendor_name: 'proveedor',
  vendor_tax_id: 'NIT',
  invoice_number: 'número de factura',
  amount: 'monto',
  currency: 'moneda',
  issue_date: 'fecha de emisión',
  due_date: 'fecha de vencimiento',
  description: 'concepto',
  beneficiary_account: 'cuenta bancaria',
  po_reference: 'orden de compra',
}
const FIELD_KEY_BY_NAME = Object.fromEntries(
  Object.entries(INVOICE_FIELD_NAMES).map(([key, name]) => [name.toLowerCase(), key]),
)
/** List fields whose items are invoice field keys: shown and typed by their Spanish name. */
const FIELD_NAME_LISTS = new Set(['required_fields'])

/** Fields that exist in the backend but do nothing in the engine: kept in the payload, not shown. */
const HIDDEN_KEYS = new Set(['period'])

const LABELS: Record<string, { label: string; hint?: string }> = {
  version: { label: 'Versión vigente', hint: 'Cada vez que guardas se crea una versión nueva.' },
  company_name: { label: 'Empresa' },
  base_currency: { label: 'Moneda base', hint: 'Los límites se miden en esta moneda.' },
  fx_rates: { label: 'Tasas de cambio', hint: 'Unidades de la moneda base por 1 unidad de cada moneda.' },
  allowed_currencies: { label: 'Monedas permitidas', hint: 'Códigos ISO separados por coma, por ejemplo USD, MXN.' },
  approval_threshold: {
    label: 'Umbral de aprobación',
    hint: 'Por encima de este monto el agente pide aprobación a una persona.',
  },
  per_payment_limit: { label: 'Límite por pago', hint: 'Tope duro por pago individual.' },
  period: { label: 'Periodo' },
  period_limit: {
    label: 'Umbral de revisión del periodo',
    hint: 'Cuando lo pagado en el periodo lo supera, cada factura nueva pasa a una persona.',
  },
  period_budget: { label: 'Presupuesto del periodo', hint: 'Informativo: hoy ninguna regla lo aplica.' },
  duplicate_window_days: {
    label: 'Ventana de duplicados (días)',
    hint: 'Días hacia atrás para detectar cobros repetidos.',
  },
  agreement_tolerance_pct: {
    label: 'Tolerancia frente al acuerdo (%)',
    hint: 'Diferencia máxima con lo acordado.',
  },
  min_extraction_confidence: {
    label: 'Confianza mínima de lectura',
    hint: 'Entre 0 y 1. Por debajo, el agente escala.',
  },
  require_allowlisted_beneficiary: {
    label: 'Solo beneficiarios permitidos',
    hint: 'Si está activo, se rechaza la factura de un proveedor que no esté en la lista.',
  },
  severity_overrides: {
    label: 'Severidad por regla',
    hint: 'Cambia si una regla incumplida rechaza o escala. Nunca puede pagar.',
  },
  period_days: { label: 'Días del periodo', hint: 'Cuántos días hacia atrás se suma lo pagado, por ejemplo 7.' },
  per_vendor_period_limit: {
    label: 'Límite por proveedor en el periodo',
    hint: 'Por encima, el pago a ese proveedor pasa a revisión humana.',
  },
  require_verified_beneficiary: {
    label: 'Solo proveedores verificados',
    hint: 'Razón social, país, datos bancarios y dueños con 25 % o más revisados por una persona.',
  },
  block_sanctioned: { label: 'Rechazar sancionados', hint: 'No se paga a personas, empresas ni países sancionados.' },
  sanctioned_countries: { label: 'Países sancionados', hint: 'Códigos ISO de dos letras separados por coma.' },
  review_on_vendor_changes: {
    label: 'Revisar cambios de cuenta, NIT o monto acordado',
    hint: 'Cuenta o NIT distintos a lo registrado o al último pago, o monto fuera de lo acordado: pasa a una persona.',
  },
  required_fields: {
    label: 'Datos obligatorios de la factura',
    hint: `Si falta alguno, la factura pasa a una persona. Separa con coma: ${Object.values(INVOICE_FIELD_NAMES).join(', ')}.`,
  },
  retention_years: { label: 'Años de conservación', hint: 'Cuánto tiempo se guardan facturas, pagos y aprobaciones.' },
  verified: { label: 'Verificado' },
  sanctioned: { label: 'Sancionado' },
  legal_name: { label: 'Razón social' },
  owners: { label: 'Dueños con 25 % o más' },
  id: { label: 'Identificador' },
  name: { label: 'Nombre' },
  tax_id: { label: 'Identificación fiscal' },
  account: { label: 'Cuenta' },
  country: { label: 'País', hint: 'Código ISO de dos letras.' },
  allowed: { label: 'Permitido' },
  beneficiary_id: { label: 'Beneficiario' },
  description: { label: 'Descripción' },
  expected_amount: { label: 'Monto acordado' },
  currency: { label: 'Moneda' },
  po_reference: { label: 'Orden de compra' },
  valid_from: { label: 'Vigente desde' },
  valid_to: { label: 'Vigente hasta' },
}

const OPTION_LABELS: Record<string, string> = {
  weekly: 'Semanal',
  monthly: 'Mensual',
  block: 'Rechazar',
  escalate: 'Escalar',
}

function humanize(key: string, title?: string) {
  const base = title ?? key.replace(/_/g, ' ')
  return base.charAt(0).toUpperCase() + base.slice(1)
}

function nonNull(schema: JsonSchema): { schema: JsonSchema; nullable: boolean } {
  if (!schema.anyOf) return { schema, nullable: false }
  const variants = schema.anyOf.filter((s) => s.type !== 'null')
  const nullable = variants.length !== schema.anyOf.length
  if (variants.length === 1) return { schema: { ...schema, ...variants[0], anyOf: undefined }, nullable }
  return { schema: { ...schema, anyOf: variants }, nullable }
}

function kindOf(schema: JsonSchema): FieldKind {
  if (schema.anyOf) {
    const types = schema.anyOf.map((s) => s.type)
    if (types.includes('number') && types.includes('string')) return 'decimal'
    return 'text'
  }
  if (schema.enum) return 'enum'
  switch (schema.type) {
    case 'boolean':
      return 'boolean'
    case 'integer':
      return 'integer'
    case 'number':
      return 'number'
    case 'array':
      return 'list'
    case 'object':
      return 'map'
    default:
      return schema.format === 'date' ? 'date' : 'text'
  }
}

const toOptions = (values?: string[]) => values?.map((v) => ({ value: v, label: OPTION_LABELS[v] ?? v }))

export function findSchema(doc: OpenApiDocument | undefined, ...names: string[]): JsonSchema | undefined {
  const schemas = doc?.components?.schemas
  if (!schemas) return undefined
  for (const name of names) if (schemas[name]) return schemas[name]
  return undefined
}

export function fieldsFrom(schema: JsonSchema, readonlyKeys: string[] = []): FieldSpec[] {
  const required = new Set(schema.required ?? [])
  return Object.entries(schema.properties ?? {}).map(([key, raw]) => {
    const { schema: s, nullable } = nonNull(raw)
    const copy = LABELS[key]
    const kind = readonlyKeys.includes(key) ? 'readonly' : kindOf(s)
    const numeric = s.anyOf?.find((v) => v.type === 'number') ?? s
    const spec: FieldSpec = {
      key,
      kind,
      label: copy?.label ?? humanize(key, raw.title),
      hint: copy?.hint ?? raw.description,
      required: required.has(key),
      nullable,
      hasDefault: raw.default !== undefined,
      defaultValue: raw.default,
      options: toOptions(s.enum),
      min: numeric.minimum ?? numeric.exclusiveMinimum,
      max: numeric.maximum,
      maxLength: s.maxLength,
    }
    if (kind === 'map' && typeof s.additionalProperties === 'object') {
      const { schema: value } = nonNull(s.additionalProperties)
      spec.valueKind = kindOf(value)
      spec.valueOptions = toOptions(value.enum)
    }
    return spec
  })
}

/** Form state keeps every scalar as a string; maps as [key, value] rows. */
export type FormValue = string | boolean | [string, string][]
export type FormValues = Record<string, FormValue>

export function toFormValues(fields: FieldSpec[], data: Record<string, unknown> | undefined): FormValues {
  const values: FormValues = {}
  for (const f of fields) {
    const v = data?.[f.key]
    // A missing boolean takes the backend default, never an invented true (it could mark a vendor sanctioned).
    if (f.kind === 'boolean') values[f.key] = v === undefined ? f.defaultValue === true : Boolean(v)
    else if (f.kind === 'map')
      values[f.key] = Object.entries((v as Record<string, unknown>) ?? {}).map(([k, x]) => [k, String(x ?? '')])
    else if (f.kind === 'list') {
      const items = Array.isArray(v) ? v.map(String) : []
      values[f.key] = (FIELD_NAME_LISTS.has(f.key) ? items.map((k) => INVOICE_FIELD_NAMES[k] ?? k) : items).join(', ')
    } else values[f.key] = v === null || v === undefined ? '' : String(v)
  }
  return values
}

const DECIMAL = /^\d+(\.\d+)?$/

export function validate(fields: FieldSpec[], values: FormValues): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const f of fields) {
    const v = values[f.key]
    if (f.kind === 'readonly' || f.kind === 'boolean' || f.kind === 'map') continue
    const text = typeof v === 'string' ? v.trim() : ''
    if (text === '') {
      if (f.required && !f.nullable) errors[f.key] = 'Este campo es obligatorio.'
      continue
    }
    if (f.kind === 'decimal' && !DECIMAL.test(text)) errors[f.key] = 'Escribe un número, por ejemplo 2500.00.'
    if (f.kind === 'integer' && !/^\d+$/.test(text)) errors[f.key] = 'Escribe un número entero.'
    if (f.kind === 'number' && Number.isNaN(Number(text))) errors[f.key] = 'Escribe un número.'
    const n = Number(text)
    if (['decimal', 'integer', 'number'].includes(f.kind) && !errors[f.key]) {
      if (f.min !== undefined && n < f.min) errors[f.key] = `Debe ser al menos ${f.min}.`
      if (f.max !== undefined && n > f.max) errors[f.key] = `Debe ser como máximo ${f.max}.`
    }
    if (f.maxLength !== undefined && text.length > f.maxLength) errors[f.key] = `Máximo ${f.maxLength} caracteres.`
    if (f.kind === 'list' && FIELD_NAME_LISTS.has(f.key)) {
      // An unknown name would be "missing" on every invoice and send all of them to a person.
      const unknown = text.split(',').map((n) => n.trim()).filter((n) => n && !(n.toLowerCase() in FIELD_KEY_BY_NAME))
      if (unknown.length) errors[f.key] = `No reconozco «${unknown.join('», «')}». Usa: ${Object.values(INVOICE_FIELD_NAMES).join(', ')}.`
    }
  }
  return errors
}

export function toPayload(fields: FieldSpec[], values: FormValues, base: Record<string, unknown> = {}) {
  const payload: Record<string, unknown> = { ...base }
  for (const f of fields) {
    const v = values[f.key]
    if (f.kind === 'readonly') continue
    if (f.kind === 'boolean') payload[f.key] = Boolean(v)
    else if (f.kind === 'map')
      payload[f.key] = Object.fromEntries(
        (v as [string, string][]).filter(([k]) => k.trim() !== '').map(([k, x]) => [k.trim(), x.trim()]),
      )
    else if (f.kind === 'list') {
      const items = String(v)
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      payload[f.key] = FIELD_NAME_LISTS.has(f.key) ? items.map((n) => FIELD_KEY_BY_NAME[n.toLowerCase()] ?? n) : items
    }
    else {
      const text = String(v).trim()
      if (text === '') {
        if (f.nullable) payload[f.key] = null
        else delete payload[f.key]
      } else if (f.kind === 'integer') payload[f.key] = Number.parseInt(text, 10)
      else if (f.kind === 'number') payload[f.key] = Number(text)
      else payload[f.key] = text
    }
  }
  return payload
}

/* ---------- Grouping and change review ---------- */

export interface FieldGroup {
  title: string
  hint?: string
  keys: string[]
  /** Rarely touched: starts folded. */
  collapsed?: boolean
}

export const RULE_GROUPS: FieldGroup[] = [
  { title: 'Datos generales', keys: ['version', 'company_name', 'base_currency'] },
  {
    title: 'Límites por pago',
    hint: 'Sobre el umbral se pide aprobación; sobre el límite el pago se rechaza.',
    keys: ['approval_threshold', 'per_payment_limit'],
  },
  {
    title: 'Pagos acumulados',
    hint: 'Lo pagado en los últimos días se compara con el umbral de revisión: por encima, cada factura nueva va a una persona.',
    keys: ['period_days', 'period_limit', 'per_vendor_period_limit', 'period_budget'],
  },
  {
    title: 'Beneficiarios',
    keys: ['require_allowlisted_beneficiary', 'require_verified_beneficiary', 'block_sanctioned', 'sanctioned_countries'],
  },
  {
    title: 'Controles de la factura',
    keys: [
      'required_fields',
      'review_on_vendor_changes',
      'duplicate_window_days',
      'agreement_tolerance_pct',
      'min_extraction_confidence',
      'retention_years',
    ],
  },
  { title: 'Monedas y tasas de cambio', keys: ['allowed_currencies', 'fx_rates'], collapsed: true },
  { title: 'Severidad por regla', keys: ['severity_overrides'], collapsed: true },
]

/** Splits fields into the known groups; anything the backend adds later lands in "Otros ajustes". */
export function groupFields(fields: FieldSpec[], groups: FieldGroup[]) {
  const byKey = new Map(fields.map((f) => [f.key, f]))
  const used = new Set<string>(HIDDEN_KEYS)
  const result = groups
    .map((g) => {
      const members = g.keys.map((k) => byKey.get(k)).filter((f): f is FieldSpec => Boolean(f))
      members.forEach((f) => used.add(f.key))
      return { group: g, fields: members }
    })
    .filter((g) => g.fields.length > 0)
  const rest = fields.filter((f) => !used.has(f.key))
  if (rest.length) result.push({ group: { title: 'Otros ajustes', keys: rest.map((f) => f.key) }, fields: rest })
  return result
}

function describeValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    return entries.length ? entries.map(([k, v]) => `${k} ${String(v)}`).join(', ') : '—'
  }
  return OPTION_LABELS[String(value)] ?? String(value)
}

export interface FieldChange {
  key: string
  label: string
  before: string
  after: string
}

/** What saving would change, field by field, in the operator's words. */
export function diffPayloads(
  fields: FieldSpec[],
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): FieldChange[] {
  return fields
    .filter((f) => f.kind !== 'readonly')
    .filter((f) => JSON.stringify(before[f.key] ?? null) !== JSON.stringify(after[f.key] ?? null))
    .map((f) => ({ key: f.key, label: f.label, before: describeValue(before[f.key]), after: describeValue(after[f.key]) }))
}
