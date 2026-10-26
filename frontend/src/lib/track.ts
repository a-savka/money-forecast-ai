import { api } from '@/api/client'
import type { components } from '@/api/schema'

type EventName = components['schemas']['EventIn']['name']

/** Продуктовая аналитика: ошибки не мешают работе приложения. */
export function track(name: EventName, props: Record<string, unknown> = {}) {
  void api.POST('/events', { body: { name, props } }).catch(() => undefined)
}

const START_KEY = 'mf-onboarding-start'

export function markOnboardingStart() {
  try {
    sessionStorage.setItem(START_KEY, String(Date.now()))
  } catch {
    // без хранилища время онбординга просто не будет посчитано
  }
}

/** Секунды с начала онбординга (или null, если старт не засечён). */
export function onboardingElapsed(): number | null {
  try {
    const start = Number(sessionStorage.getItem(START_KEY))
    return start ? Math.round((Date.now() - start) / 1000) : null
  } catch {
    return null
  }
}

export function clearOnboardingStart() {
  try {
    sessionStorage.removeItem(START_KEY)
  } catch {
    // ничего страшного
  }
}
