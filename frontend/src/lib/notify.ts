import { Capacitor } from '@capacitor/core'
import { LocalNotifications } from '@capacitor/local-notifications'

import type { Alert } from '@/api/types'
import { useToasts } from '@/store/toast'

const SEEN_KEY = 'mf-notified'

/** Числовой id для Android из строкового id алерта. */
function numericId(id: string) {
  let h = 0
  for (const ch of id) h = (Math.imul(31, h) + ch.charCodeAt(0)) | 0
  return Math.abs(h) % 2_000_000_000
}

export function isNative() {
  return Capacitor.isNativePlatform()
}

export async function ensurePermission(): Promise<boolean> {
  if (!isNative()) return true
  const current = await LocalNotifications.checkPermissions()
  if (current.display === 'granted') return true
  const asked = await LocalNotifications.requestPermissions()
  return asked.display === 'granted'
}

/** Android — системное уведомление; веб — toast внутри приложения. */
export async function notify(alert: Alert) {
  if (isNative() && (await ensurePermission())) {
    await LocalNotifications.schedule({
      notifications: [
        { id: numericId(alert.id), title: alert.title, body: alert.body, extra: { link: alert.link } },
      ],
    })
    return
  }
  useToasts.getState().push(alert)
}

export function loadSeen(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]') as string[])
  } catch {
    return new Set()
  }
}

export function saveSeen(seen: Set<string>) {
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify([...seen].slice(-100)))
  } catch {
    // хранилище недоступно — в худшем случае уведомление покажется повторно
  }
}
