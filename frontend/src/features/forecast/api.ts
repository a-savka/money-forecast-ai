import { useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { ForecastResult, Horizon, StrategyInfo } from '@/api/types'
import { useSettings } from '@/store/settings'

export function useForecast(horizon: Horizon = 'month') {
  const strategy = useSettings((s) => s.strategy)
  return useQuery({
    queryKey: ['forecast', strategy, horizon],
    queryFn: () => unwrap<ForecastResult>(api.GET('/forecast', { params: { query: { strategy, horizon } } })),
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
