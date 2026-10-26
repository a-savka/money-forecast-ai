import { useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { ForecastResult, Horizon, StrategyInfo } from '@/api/types'
import { useSettings } from '@/store/settings'

/** Прогноз; horizon = undefined — ждём, пока станет известен тариф (Free — неделя). */
export function useForecast(horizon: Horizon | undefined) {
  const strategy = useSettings((s) => s.strategy)
  return useQuery({
    queryKey: ['forecast', strategy, horizon],
    queryFn: () => unwrap<ForecastResult>(api.GET('/forecast', { params: { query: { strategy, horizon } } })),
    enabled: horizon !== undefined,
    retry: false,
  })
}

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => unwrap<StrategyInfo[]>(api.GET('/forecast/strategies')),
    staleTime: Infinity,
  })
}
