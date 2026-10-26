import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { Horizon, Subscription, SubscriptionAction } from '@/api/types'
import { useSession, type User } from '@/store/session'

export function useSubscription() {
  return useQuery({
    queryKey: ['subscription'],
    queryFn: () => unwrap<Subscription>(api.GET('/mock/subscription')),
  })
}

/** Есть ли доступ к Premium-функциям (подписка или пробный период). */
export function useIsPremium() {
  const { data } = useSubscription()
  return data ? data.plan !== 'free' : false
}

/** Горизонт прогноза по умолчанию: Free — неделя, Premium — месяц. */
export function usePlanHorizon(): Horizon | undefined {
  const { data } = useSubscription()
  if (!data) return undefined
  return data.plan === 'free' ? 'week' : 'month'
}

export function useChangeSubscription() {
  const qc = useQueryClient()
  const setUser = useSession((s) => s.setUser)
  return useMutation({
    mutationFn: (action: SubscriptionAction) =>
      unwrap<Subscription>(api.POST('/mock/subscription', { body: { action } })),
    onSuccess: async (data) => {
      qc.setQueryData(['subscription'], data)
      const me = await unwrap<User>(api.GET('/auth/me'))
      setUser(me)
      await Promise.all(
        ['forecast', 'recommendations'].map((key) => qc.invalidateQueries({ queryKey: [key] })),
      )
    },
  })
}
