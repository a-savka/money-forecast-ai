import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, unwrap } from '@/api/client'
import type { Alert } from '@/api/types'
import { isNative, loadSeen, notify, saveSeen } from '@/lib/notify'
import { useSettings } from '@/store/settings'

export function useAlerts() {
  const strategy = useSettings((s) => s.strategy)
  const enabled = useSettings((s) => s.notificationsEnabled)
  return useQuery({
    queryKey: ['notifications', strategy],
    queryFn: () => unwrap<Alert[]>(api.GET('/mock/notifications', { params: { query: { strategy } } })),
    enabled,
    staleTime: 5 * 60_000,
    refetchInterval: 15 * 60_000,
  })
}

/** Показывает новые алерты (риск разрыва, лимиты, платежи) один раз. */
export function useAlertsNotifier() {
  const { data } = useAlerts()
  const navigate = useNavigate()

  useEffect(() => {
    if (!data?.length) return
    const seen = loadSeen()
    const fresh = data.filter((a) => !seen.has(a.id))
    fresh.forEach((a) => seen.add(a.id))
    saveSeen(seen)
    fresh.forEach((a) => void notify(a))
  }, [data])

  // Нажатие на системное уведомление открывает нужный экран
  useEffect(() => {
    if (!isNative()) return
    let remove: (() => void) | undefined
    void import('@capacitor/local-notifications').then(({ LocalNotifications }) =>
      LocalNotifications.addListener('localNotificationActionPerformed', (e) => {
        const link = e.notification.extra?.link as string | undefined
        if (link) navigate(link)
      }).then((h) => (remove = () => void h.remove())),
    )
    return () => remove?.()
  }, [navigate])
}

export function useTestNotification() {
  return useMutation({
    mutationFn: () => unwrap<Alert>(api.POST('/mock/push/test')),
    onSuccess: (a) => notify({ ...a, id: `${a.id}-${Date.now()}` }),
  })
}
