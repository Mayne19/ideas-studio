const BASE_URL = (import.meta.env['VITE_API_URL'] as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Traduit une erreur d'appel API en message affichable — les échecs réseau
 * bruts (fetch() qui rejette avant même d'obtenir une réponse HTTP : DNS,
 * CORS, serveur injoignable pendant un redéploiement...) remontent avec le
 * message natif du navigateur ("NetworkError when attempting to fetch
 * resource.", "Failed to fetch"...), illisible et en anglais. */
export function friendlyApiErrorMessage(err: unknown, fallback = 'Une erreur est survenue.'): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof TypeError || (err instanceof Error && /networkerror|failed to fetch/i.test(err.message))) {
    return 'Impossible de contacter le serveur. Vérifiez votre connexion et réessayez dans quelques instants (le backend est peut-être en cours de redémarrage).'
  }
  if (err instanceof Error) return err.message || fallback
  return fallback
}

type RequestOptions = {
  method?: string
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
}

type ApiCallOptions = Pick<RequestOptions, 'signal' | 'timeoutMs'>

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const controller = new AbortController()
  const timeoutMs = options.timeoutMs ?? 25000
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  if (options.signal) {
    if (options.signal.aborted) controller.abort()
    else options.signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(408, 'La requête a pris trop de temps. Réessayez dans un instant.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }

  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new ApiError(401, 'Session expirée. Veuillez vous reconnecter.')
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: unknown }
    const detail = data.detail
    let message: string
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const structured = detail as { message?: string; reasons?: string[] }
      const reasons = Array.isArray(structured.reasons) && structured.reasons.length > 0
        ? ` ${structured.reasons.join(' ')}`
        : ''
      message = `${structured.message ?? `Erreur ${res.status}`}${reasons}`
    } else if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      message = first.msg ?? `Erreur ${res.status}`
    } else {
      message = `Erreur ${res.status}`
    }
    throw new ApiError(res.status, message)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function healthCheck(): Promise<{ status: string }> {
  return api.get<{ status: string }>('/health')
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) =>
    request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown, options: ApiCallOptions = {}) =>
    request<T>(path, { method: 'POST', body, ...options }),
  put: <T>(path: string, body?: unknown, options: ApiCallOptions = {}) =>
    request<T>(path, { method: 'PUT', body, ...options }),
  patch: <T>(path: string, body?: unknown, options: ApiCallOptions = {}) =>
    request<T>(path, { method: 'PATCH', body, ...options }),
  delete: <T>(path: string, options: ApiCallOptions = {}) =>
    request<T>(path, { method: 'DELETE', ...options }),
}
