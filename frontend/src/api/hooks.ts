import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { json, request } from './client'
import type {
  Agreement,
  ApprovalRequest,
  Beneficiary,
  ChatMessage,
  ConversationSummary,
  Decision,
  Invoice,
  RuleSet,
  SendMessageResponse,
  Summary,
} from './types'

export const keys = {
  health: ['health'] as const,
  conversations: ['conversations'] as const,
  messages: (id: string) => ['conversations', id, 'messages'] as const,
  invoices: ['invoices'] as const,
  invoice: (id: string) => ['invoices', id] as const,
  invoiceDecisions: (id: string) => ['invoices', id, 'decisions'] as const,
  decisions: ['decisions'] as const,
  summary: ['summary'] as const,
  rules: ['rules'] as const,
  beneficiaries: ['beneficiaries'] as const,
  agreements: ['agreements'] as const,
  openapi: ['openapi'] as const,
}

export const useHealth = () =>
  useQuery({
    queryKey: keys.health,
    queryFn: () => request<{ status: string }>('/health'),
    refetchInterval: (query) => (query.state.status === 'error' ? 5_000 : 30_000),
    retry: false,
  })

export const useConversations = () =>
  useQuery({
    queryKey: keys.conversations,
    queryFn: () => request<ConversationSummary[]>('/api/conversations'),
  })

export const useMessages = (conversationId: string | undefined) =>
  useQuery({
    queryKey: keys.messages(conversationId ?? ''),
    queryFn: () => request<ChatMessage[]>(`/api/conversations/${conversationId}/messages`),
    enabled: Boolean(conversationId),
  })

export const useInvoice = (invoiceId: string | null | undefined) =>
  useQuery({
    queryKey: keys.invoice(invoiceId ?? ''),
    queryFn: () => request<Invoice>(`/api/invoices/${invoiceId}`),
    enabled: Boolean(invoiceId),
  })

export const useInvoices = () =>
  useQuery({ queryKey: keys.invoices, queryFn: () => request<Invoice[]>('/api/invoices') })

export const useInvoiceDecisions = (invoiceId: string | null | undefined) =>
  useQuery({
    queryKey: keys.invoiceDecisions(invoiceId ?? ''),
    queryFn: () => request<Decision[]>(`/api/invoices/${invoiceId}/decisions`),
    enabled: Boolean(invoiceId),
  })

export const useDecisions = () =>
  useQuery({ queryKey: keys.decisions, queryFn: () => request<Decision[]>('/api/decisions') })

export const useSummary = () =>
  useQuery({ queryKey: keys.summary, queryFn: () => request<Summary>('/api/summary') })

export const useRules = () =>
  useQuery({ queryKey: keys.rules, queryFn: () => request<RuleSet>('/api/rules'), retry: false })

export const useBeneficiaries = () =>
  useQuery({
    queryKey: keys.beneficiaries,
    queryFn: () => request<Beneficiary[]>('/api/beneficiaries'),
  })

export const useAgreements = () =>
  useQuery({ queryKey: keys.agreements, queryFn: () => request<Agreement[]>('/api/agreements') })

export interface JsonSchema {
  type?: string
  title?: string
  description?: string
  enum?: string[]
  anyOf?: JsonSchema[]
  items?: JsonSchema
  properties?: Record<string, JsonSchema>
  additionalProperties?: JsonSchema | boolean
  required?: string[]
  default?: unknown
  minimum?: number
  maximum?: number
  exclusiveMinimum?: number
  minLength?: number
  maxLength?: number
  format?: string
  readOnly?: boolean
}

export interface OpenApiDocument {
  components?: { schemas?: Record<string, JsonSchema> }
}

/** The backend's own OpenAPI document: the settings forms are generated from it. */
export const useOpenApi = () =>
  useQuery({
    queryKey: keys.openapi,
    queryFn: () => request<OpenApiDocument>('/openapi.json'),
    staleTime: Infinity,
  })

function invalidateActivity(qc: QueryClient) {
  void qc.invalidateQueries({ queryKey: keys.conversations })
  void qc.invalidateQueries({ queryKey: keys.invoices })
  void qc.invalidateQueries({ queryKey: keys.decisions })
  void qc.invalidateQueries({ queryKey: keys.summary })
}

export function useSendMessage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (input: { conversationId?: string; text?: string; file?: File }) => {
      const conversationId =
        input.conversationId ??
        (await request<ConversationSummary>('/api/conversations', { method: 'POST', ...json({}) })).id
      const body = new FormData()
      if (input.text) body.append('text', input.text)
      if (input.file) body.append('file', input.file)
      const result = await request<SendMessageResponse>(
        `/api/conversations/${conversationId}/messages`,
        { method: 'POST', body },
      )
      return { conversationId, result }
    },
    onSuccess: ({ conversationId, result }) => {
      qc.setQueryData<ChatMessage[]>(keys.messages(conversationId), (old) => [
        ...(old ?? []),
        result.user_message,
        result.assistant_message,
      ])
      if (result.invoice) qc.setQueryData(keys.invoice(result.invoice.id), result.invoice)
      invalidateActivity(qc)
    },
  })
}

export function useResolveInvoice(invoiceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { action: 'approve' | 'reject' } & ApprovalRequest) =>
      request<Decision>(`/api/invoices/${invoiceId}/${input.action}`, {
        method: 'POST',
        ...json({ approver: input.approver, comment: input.comment || null }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.invoice(invoiceId) })
      void qc.invalidateQueries({ queryKey: keys.invoiceDecisions(invoiceId) })
      invalidateActivity(qc)
    },
  })
}

/** Re-run the rules on an invoice (e.g. after adding its beneficiary). Creates a new agent decision. */
export function useReevaluate(invoiceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => request<Decision>(`/api/invoices/${invoiceId}/reevaluate`, { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.invoice(invoiceId) })
      void qc.invalidateQueries({ queryKey: keys.invoiceDecisions(invoiceId) })
      invalidateActivity(qc)
    },
  })
}

/** Demo control: wipe invoices, decisions and chats, then reload the company from the dataset. */
export function useResetDemo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => request<{ ok: boolean }>('/api/dev/reset', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export function useSaveRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (rules: Record<string, unknown>) =>
      request<RuleSet>('/api/rules', { method: 'PUT', ...json(rules) }),
    onSuccess: (saved) => {
      qc.setQueryData(keys.rules, saved)
      void qc.invalidateQueries({ queryKey: keys.summary })
    },
  })
}

export function useSaveBeneficiary() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: Record<string, unknown>) =>
      request<Beneficiary>('/api/beneficiaries', { method: 'POST', ...json(b) }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.beneficiaries }),
  })
}

export function useDeleteBeneficiary() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      request<void>(`/api/beneficiaries/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.beneficiaries }),
  })
}

export function useSaveAgreement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (a: Record<string, unknown>) =>
      request<Agreement>('/api/agreements', { method: 'POST', ...json(a) }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.agreements }),
  })
}
