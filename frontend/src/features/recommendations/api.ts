import { useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { RecommendationsOut } from '@/api/types'
import { useSettings } from '@/store/settings'

export function useRecommendations() {
  const strategy = useSettings((s) => s.strategy)
  const mode = useSettings((s) => s.recommendationsMode)
  return useQuery({
    queryKey: ['recommendations', strategy, mode],
    queryFn: () =>
      unwrap<RecommendationsOut>(api.GET('/recommendations', { params: { query: { strategy, mode } } })),
    retry: false,
  })
}
