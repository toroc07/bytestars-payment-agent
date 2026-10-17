// Aliases over the generated OpenAPI types (schema.d.ts, regenerate with `npm run gen:api`).
import type { components } from './schema'

type S = components['schemas']

export type Outcome = S['Outcome']
export type InvoiceStatus = S['InvoiceStatus']
export type CheckStatus = S['CheckStatus']
export type Actor = S['Actor']
export type ExtractedInvoice = S['ExtractedInvoice']
export type Invoice = S['Invoice']
export type RuleCheck = S['RuleCheck']
export type Decision = S['Decision']
export type ChatMessage = S['ChatMessage']
export type ConversationSummary = S['ConversationSummary']
export type SendMessageResponse = S['SendMessageResponse']
export type Summary = S['SummaryResponse']
export type RuleSet = S['RuleSet-Output']
export type Beneficiary = S['Beneficiary']
export type Agreement = S['Agreement-Output']
export type ApprovalRequest = S['ApprovalRequest']
