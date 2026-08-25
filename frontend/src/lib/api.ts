/**
 * HTTP client.
 *
 * One place for the base URL, the bearer token, and error shaping, so every
 * screen surfaces failures the same way and no component talks to fetch()
 * directly.
 */

const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
export const API_BASE = RAW_BASE.replace(/\/$/, '')

const TOKEN_KEY = 'nookr.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* Storage can be unavailable in private modes; the session still works. */
  }
}

export interface ApiErrorDetail {
  field?: string
  message: string
}

/** Every failure the UI can show, in one shape. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: ApiErrorDetail[] | unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details ?? null
  }

  /** Field errors keyed by field name, for inline form messages. */
  get fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {}
    const map: Record<string, string> = {}
    for (const item of this.details as ApiErrorDetail[]) {
      if (item?.field) map[item.field] = item.message
    }
    return map
  }

  get isAuthError(): boolean {
    return this.status === 401
  }
}

/** Raised when the API cannot be reached at all. */
export class NetworkError extends ApiError {
  constructor(message: string) {
    super(0, 'network_error', message)
    this.name = 'NetworkError'
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

interface RequestOptions {
  method?: Method
  body?: unknown
  query?: Record<string, string | number | boolean | undefined | null>
  signal?: AbortSignal
  /** Skip the Authorization header (used by the public endpoints). */
  anonymous?: boolean
}

let onUnauthorized: (() => void) | null = null

/** Registered by the auth provider so a dead token logs the user out once. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  const qs = params.toString()
  return qs ? `${url}?${qs}` : url
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, signal, anonymous } = options

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (!anonymous) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if ((error as Error)?.name === 'AbortError') throw error
    throw new NetworkError(
      'Cannot reach the Nookr API. Check that the backend is running on port 8000.',
    )
  }

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const envelope = (payload as { error?: { code?: string; message?: string; details?: unknown } })
      ?.error
    const error = new ApiError(
      response.status,
      envelope?.code ?? `http_${response.status}`,
      envelope?.message ?? 'Something went wrong. Please try again.',
      envelope?.details,
    )
    if (error.isAuthError && !anonymous) onUnauthorized?.()
    throw error
  }

  return payload as T
}

export const api = {
  get: <T,>(path: string, query?: RequestOptions['query'], signal?: AbortSignal) =>
    request<T>(path, { method: 'GET', query, signal }),
  post: <T,>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T,>(path: string) => request<T>(path, { method: 'DELETE' }),
}

/** Human-readable message for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong. Please try again.'
}
