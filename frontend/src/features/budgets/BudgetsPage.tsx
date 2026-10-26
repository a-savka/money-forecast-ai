import { ArrowLeft, Crown, Gauge, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useCategories } from '@/api/hooks'
import { ApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { EmptyState, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { Input, Label, Select } from '@/components/ui/input'
import { formatMoney } from '@/lib/utils'

import { BudgetCard } from './BudgetCard'
import { useBudgetSuggestions, useBudgets, useDeleteBudget, useSaveBudget } from './api'

export function BudgetsPage() {
  const { data: budgets, isLoading, error } = useBudgets()
  const { data: categories = [] } = useCategories()
  const { data: suggestions = [] } = useBudgetSuggestions()
  const save = useSaveBudget()
  const remove = useDeleteBudget()
  const byId = new Map(categories.map((c) => [c.id, c]))
  const used = new Set(budgets?.map((b) => b.category_id))
  const expenseCats = categories.filter((c) => c.kind === 'expense')

  const [categoryId, setCategoryId] = useState<number>()
  const [limit, setLimit] = useState('')
  const needsPremium = save.error instanceof ApiError && save.error.status === 402

  const submit = (cid: number, value: number) =>
    save.mutate(
      { category_id: cid, limit: value },
      {
        onSuccess: () => {
          setCategoryId(undefined)
          setLimit('')
        },
      },
    )

  return (
    <div className="mx-auto min-h-full max-w-md space-y-4 bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/more" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Лимиты по категориям</h1>
      </header>

      {isLoading && <PageLoader />}
      {error && <ErrorMessage error={error} />}
      {budgets && budgets.length === 0 && (
        <EmptyState icon={<Gauge className="h-8 w-8" />} title="Лимитов пока нет">
          Задайте месячный лимит — и мы заранее скажем, когда он закончится при вашем темпе трат.
        </EmptyState>
      )}
      {budgets && budgets.length > 0 && (
        <Card>
          <ul className="divide-y divide-slate-100">
            {budgets.map((b) => (
              <li key={b.id} className="flex items-start gap-2 py-3">
                <div className="min-w-0 flex-1">
                  <BudgetCard budget={b} category={byId.get(b.category_id)} />
                </div>
                <button
                  onClick={() => remove.mutate(b.id)}
                  className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                  aria-label="Удалить лимит"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-slate-500">
            Светлая часть полосы — сколько уйдёт к концу месяца при текущем темпе.
          </p>
        </Card>
      )}

      <Card className="space-y-3">
        <CardTitle>Новый лимит на месяц</CardTitle>
        {suggestions.filter((s) => !used.has(s.category_id)).length > 0 && (
          <div>
            <p className="mb-1 text-xs text-slate-500">По вашим тратам за 3 месяца:</p>
            <div className="flex flex-wrap gap-2">
              {suggestions
                .filter((s) => !used.has(s.category_id))
                .slice(0, 4)
                .map((s) => (
                  <button
                    key={s.category_id}
                    onClick={() => {
                      setCategoryId(s.category_id)
                      setLimit(String(s.limit))
                    }}
                    className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm hover:border-brand-500"
                  >
                    {byId.get(s.category_id)?.name} · {formatMoney(s.limit)}
                  </button>
                ))}
            </div>
          </div>
        )}
        <div className="space-y-1">
          <Label htmlFor="budget-category">Категория</Label>
          <Select
            id="budget-category"
            value={categoryId ?? ''}
            onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">Выберите категорию</option>
            {expenseCats.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {used.has(c.id) ? ' (изменить)' : ''}
              </option>
            ))}
          </Select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="budget-limit">Лимит, ₽</Label>
          <Input
            id="budget-limit"
            inputMode="decimal"
            value={limit}
            onChange={(e) => setLimit(e.target.value.replace(',', '.'))}
            placeholder="10000"
          />
        </div>
        <Button
          className="w-full"
          disabled={!categoryId || !(Number(limit) > 0) || save.isPending}
          onClick={() => categoryId && submit(categoryId, Number(limit))}
        >
          Сохранить
        </Button>
        {needsPremium ? (
          <Link to="/premium" className="flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-sm">
            <Crown className="h-5 w-5 shrink-0 text-amber-500" />
            В Free доступен один лимит. Больше — в Premium, 7 дней бесплатно.
          </Link>
        ) : (
          save.error && <ErrorMessage error={save.error} />
        )}
      </Card>
    </div>
  )
}
