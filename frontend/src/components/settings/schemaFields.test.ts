import { describe, expect, it } from 'vitest'
import type { JsonSchema } from '@/api/hooks'
import { diffPayloads, fieldsFrom, groupFields, RULE_GROUPS, toFormValues, toPayload, validate } from './schemaFields'

// Shapes taken from the backend's OpenAPI (RuleSet-Input / Agreement-Input).
const ruleSet: JsonSchema = {
  type: 'object',
  required: ['approval_threshold', 'period', 'allowed_currencies'],
  properties: {
    version: { type: 'integer', default: 1 },
    approval_threshold: { anyOf: [{ type: 'number', exclusiveMinimum: 0 }, { type: 'string' }] },
    period: { type: 'string', enum: ['weekly', 'monthly'] },
    allowed_currencies: { type: 'array', items: { type: 'string' } },
    min_extraction_confidence: { type: 'number', minimum: 0, maximum: 1 },
    require_allowlisted_beneficiary: { type: 'boolean', default: true },
    severity_overrides: {
      type: 'object',
      additionalProperties: { type: 'string', enum: ['block', 'escalate'] },
    },
    brand_new_rule: { type: 'integer', title: 'Brand New Rule' },
  },
}

const agreement: JsonSchema = {
  type: 'object',
  required: ['beneficiary_id'],
  properties: {
    beneficiary_id: { type: 'string' },
    po_reference: { anyOf: [{ type: 'string' }, { type: 'null' }] },
    valid_from: { anyOf: [{ type: 'string', format: 'date' }, { type: 'null' }] },
  },
}

describe('fieldsFrom', () => {
  const fields = fieldsFrom(ruleSet, ['version'])
  const byKey = Object.fromEntries(fields.map((f) => [f.key, f]))

  it('maps each JSON Schema shape to a control', () => {
    expect(byKey.version.kind).toBe('readonly')
    expect(byKey.approval_threshold.kind).toBe('decimal')
    expect(byKey.period.kind).toBe('enum')
    expect(byKey.allowed_currencies.kind).toBe('list')
    expect(byKey.min_extraction_confidence.kind).toBe('number')
    expect(byKey.require_allowlisted_beneficiary.kind).toBe('boolean')
    expect(byKey.severity_overrides.kind).toBe('map')
    expect(byKey.severity_overrides.valueOptions?.map((o) => o.value)).toEqual(['block', 'escalate'])
  })

  it('labels known fields in Spanish and still shows unknown ones', () => {
    expect(byKey.approval_threshold.label).toBe('Umbral de aprobación')
    expect(byKey.period.options?.map((o) => o.label)).toEqual(['Semanal', 'Mensual'])
    expect(byKey.brand_new_rule.label).toBe('Brand New Rule')
  })

  it('treats anyOf with null as an optional field', () => {
    const a = Object.fromEntries(fieldsFrom(agreement).map((f) => [f.key, f]))
    expect(a.po_reference).toMatchObject({ kind: 'text', nullable: true })
    expect(a.valid_from).toMatchObject({ kind: 'date', nullable: true })
  })
})

describe('validate and toPayload', () => {
  const fields = fieldsFrom(ruleSet, ['version'])
  const data = {
    version: 3,
    approval_threshold: '5000.00',
    period: 'monthly',
    allowed_currencies: ['USD', 'MXN'],
    min_extraction_confidence: 0.8,
    require_allowlisted_beneficiary: true,
    severity_overrides: { R03: 'block' },
    brand_new_rule: 2,
  }

  it('round-trips server data without changes', () => {
    const values = toFormValues(fields, data)
    expect(validate(fields, values)).toEqual({})
    expect(toPayload(fields, values, data)).toEqual(data)
  })

  it('rejects malformed numbers and out-of-range values', () => {
    const values = toFormValues(fields, data)
    values.approval_threshold = '5,000'
    values.min_extraction_confidence = '1.5'
    values.period = ''
    const errors = validate(fields, values)
    expect(errors.approval_threshold).toMatch(/número/)
    expect(errors.min_extraction_confidence).toMatch(/como máximo 1/)
    expect(errors.period).toMatch(/obligatorio/)
  })

  it('parses lists and drops empty map rows', () => {
    const values = toFormValues(fields, data)
    values.allowed_currencies = ' USD,  EUR ,, '
    values.severity_overrides = [
      ['R03', 'escalate'],
      ['  ', 'block'],
    ]
    const payload = toPayload(fields, values, data)
    expect(payload.allowed_currencies).toEqual(['USD', 'EUR'])
    expect(payload.severity_overrides).toEqual({ R03: 'escalate' })
  })

  it('sends null for an emptied optional field', () => {
    const f = fieldsFrom(agreement)
    const payload = toPayload(f, toFormValues(f, { beneficiary_id: 'b1', po_reference: 'PO-1' }), {})
    expect(payload).toMatchObject({ beneficiary_id: 'b1', po_reference: 'PO-1', valid_from: null })
  })
})

describe('groupFields and diffPayloads', () => {
  const fields = fieldsFrom(ruleSet, ['version'])

  it('places known fields in their group and new backend fields in "Otros ajustes"', () => {
    const groups = groupFields(fields, RULE_GROUPS)
    const titles = groups.map((g) => g.group.title)
    expect(titles).toContain('Límites por pago')
    expect(titles[titles.length - 1]).toBe('Otros ajustes')
    expect(groups.at(-1)?.fields.map((f) => f.key)).toEqual(['brand_new_rule'])
    expect(groups.find((g) => g.group.title === 'Severidad por regla')?.group.collapsed).toBe(true)
  })

  it('describes each change in the operator words', () => {
    const before = { approval_threshold: '5000.00', period: 'monthly', require_allowlisted_beneficiary: true }
    const after = { approval_threshold: '8000.00', period: 'weekly', require_allowlisted_beneficiary: true }
    expect(diffPayloads(fields, before, after)).toEqual([
      { key: 'approval_threshold', label: 'Umbral de aprobación', before: '5000.00', after: '8000.00' },
      { key: 'period', label: 'Periodo', before: 'Mensual', after: 'Semanal' },
    ])
    expect(diffPayloads(fields, before, { ...before })).toEqual([])
  })
})

describe('boolean defaults', () => {
  // Shape of the backend Beneficiary after Dev C's rules (verified defaults to true there).
  const beneficiary: JsonSchema = {
    type: 'object',
    required: ['id', 'name'],
    properties: {
      id: { type: 'string' },
      name: { type: 'string' },
      allowed: { type: 'boolean', default: true },
      verified: { type: 'boolean', default: true },
      sanctioned: { type: 'boolean', default: false },
      owners: { type: 'array', items: { type: 'string' } },
    },
  }
  const fields = fieldsFrom(beneficiary)

  it('takes the backend default for a missing boolean instead of inventing true', () => {
    const values = toFormValues(fields, {})
    expect(values.sanctioned).toBe(false)
    expect(values.allowed).toBe(true)
  })

  it('lets a new vendor start unverified and not sanctioned', () => {
    const start = { verified: false, sanctioned: false, allowed: true }
    const payload = toPayload(fields, toFormValues(fields, start), start)
    expect(payload).toMatchObject({ verified: false, sanctioned: false, allowed: true, owners: [] })
  })
})
