import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from './client'
import type { Account, Category, Transaction, TransactionIn, TransactionPatch } from './types'

export const qk = {
  categories: ['categories'] as const,
  accounts: ['accounts'] as const,
  transactions: (filters: TransactionFilters) => ['transactions', filters] as const,
}

export function useCategories() {
  return useQuery({
    queryKey: qk.categories,
    queryFn: () => unwrap<Category[]>(api.GET('/categories')),
    staleTime: Infinity,
  })
}

export function useCategoryMap() {
  const { data } = useCategories()
  return new Map((data ?? []).map((c) => [c.id, c]))
}

export function useAccounts() {
  return useQuery({ queryKey: qk.accounts, queryFn: () => unwrap<Account[]>(api.GET('/accounts')) })
}

export interface TransactionFilters {
  q?: string
  kind?: 'expense' | 'income'
  category_id?: number
}

const PAGE = 50

export function useTransactions(filters: TransactionFilters) {
  return useInfiniteQuery({
    queryKey: qk.transactions(filters),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/transactions', {
          params: { query: { ...filters, q: filters.q || undefined, limit: PAGE, offset: pageParam } },
        }),
      ),
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, p) => n + p.items.length, 0)
      return loaded < last.total ? loaded : undefined
    },
    placeholderData: keepPreviousData,
  })
}

/** После изменения операций инвалидируем всё, что от них зависит. */
export function useInvalidateFinance() {
  const qc = useQueryClient()
  return () =>
    Promise.all(
      ['transactions', 'accounts', 'analytics', 'forecast', 'recommendations'].map((key) =>
        qc.invalidateQueries({ queryKey: [key] }),
      ),
    )
}

export function useCreateTransaction() {
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: (body: TransactionIn) => unwrap<Transaction>(api.POST('/transactions', { body })),
    onSuccess: invalidate,
  })
}

export function useUpdateTransaction() {
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: TransactionPatch }) =>
      unwrap<Transaction>(api.PATCH('/transactions/{tx_id}', { params: { path: { tx_id: id } }, body })),
    onSuccess: invalidate,
  })
}

export function useDeleteTransaction() {
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/transactions/{tx_id}', { params: { path: { tx_id: id } } })),
    onSuccess: invalidate,
  })
}
