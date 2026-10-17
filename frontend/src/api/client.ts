const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Network failures (backend down) surface as status 0. */
export function isOffline(error: unknown): boolean {
  return error instanceof ApiError && error.status === 0
}

function describe(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    if (first?.msg) return `Datos inválidos: ${first.msg}`
  }
  if (status === 413) return 'El archivo es demasiado grande.'
  if (status === 429) return 'Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.'
  if (status >= 500) return 'El servidor tuvo un problema. Inténtalo de nuevo.'
  return `La solicitud falló (${status}).`
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(0, 'No hay conexión con el servidor del agente.')
  }

  if (!response.ok) {
    let detail: unknown = null
    try {
      detail = ((await response.json()) as { detail?: unknown }).detail
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(response.status, describe(detail, response.status))
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const json = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})
