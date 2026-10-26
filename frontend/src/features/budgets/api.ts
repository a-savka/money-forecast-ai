import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { BudgetStatus, BudgetSuggestion } from '@/api/types'

const key = ['budgets']

export function useBudgets() {
  return useQuery({ queryKey: key, queryFn: () => unwrap<BudgetStatus[]>(api.GET('/mock/budgets')) })
}

export function useBudgetSuggestions() {
  return useQuery({
    queryKey: [...key, 'suggest'],
    queryFn: () => unwrap<BudgetSuggestion[]>(api.GET('/mock/budgets/suggest')),
  })
}

export function useSaveBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { category_id: number; limit: number }) =>
      unwrap<BudgetStatus[]>(api.PUT('/mock/budgets', { body })),
    onSuccess: (data) => qc.setQueryData(key, data),
  })
}

export function useDeleteBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      unwrap<BudgetStatus[]>(api.DELETE('/mock/budgets/{budget_id}', { params: { path: { budget_id: id } } })),
    onSuccess: (data) => qc.setQueryData(key, data),
  })
}
