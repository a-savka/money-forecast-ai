import createClient, { type Middleware } from 'openapi-fetch'

import { useSession } from '@/store/session'

import type { paths } from './schema'

const API_URL_KEY = 'mf-api-url'
const DEFAULT_API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Адрес API можно переопределить в приложении — удобно для APK в локальной сети. */
export function getApiUrl(): string {
  try {
    return localStorage.getItem(API_URL_KEY) || DEFAULT_API_URL
  } catch {
    return DEFAULT_API_URL
  }
}

export function setApiUrl(url: string) {
  try {
    if (url.trim()) localStorage.setItem(API_URL_KEY, url.trim().replace(/\/$/, ''))
    else localStorage.removeItem(API_URL_KEY)
  } catch {
    // localStorage недоступен — используем адрес по умолчанию
  }
}

const auth: Middleware = {
  onRequest({ request }) {
    // Подменяем базовый адрес на актуальный (мог измениться в настройках)
    const base = getApiUrl()
    if (!request.url.startsWith(base)) {
      const path = request.url.replace(/^https?:\/\/[^/]+/, '')
      request = new Request(base + path, request)
    }
    const token = useSession.getState().token
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401) useSession.getState().logout()
    return response
  },
}

export const api = createClient<paths>({ baseUrl: DEFAULT_API_URL })
api.use(auth)

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Достаёт data из ответа openapi-fetch или бросает ApiError — удобно для TanStack Query. */
export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promise
  if (error !== undefined || !response.ok) {
    const detail = (error as { detail?: unknown } | undefined)?.detail
    const message = typeof detail === 'string' ? detail : `Ошибка ${response.status}`
    throw new ApiError(response.status, message)
  }
  return data as T
}

export type { components } from './schema'
