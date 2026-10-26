import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { BacktestRequest, BacktestRun } from '@/api/types'

export function useExperiments() {
  return useQuery({
    queryKey: ['experiments'],
    queryFn: () => unwrap<BacktestRun[]>(api.GET('/experiments', { params: { query: { limit: 20 } } })),
  })
}

export function useRunBacktest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: BacktestRequest) => unwrap<BacktestRun[]>(api.POST('/experiments/backtest', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['experiments'] }),
  })
}

/** Последний запуск — прогоны с одинаковым набором параметров, сделанные одним запросом. */
export function latestBatch(runs: BacktestRun[]): BacktestRun[] {
  if (!runs.length) return []
  const first = runs[0]
  const t = new Date(first.created_at).getTime()
  return runs.filter(
    (r) => r.dataset === first.dataset && Math.abs(new Date(r.created_at).getTime() - t) < 60_000,
  )
}
