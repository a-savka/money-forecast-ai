import { Plus, Search, Wallet } from 'lucide-react'
import { useDeferredValue, useMemo, useState } from 'react'

import { useAccounts, useCategoryMap, useTransactions, type TransactionFilters } from '@/api/hooks'
import type { Transaction } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { PageHeader } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { EmptyState, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { Input } from '@/components/ui/input'
import { Sheet } from '@/components/ui/sheet'
import { cn, formatDate, formatMoney } from '@/lib/utils'

import { TransactionForm } from './TransactionForm'

const KINDS: { value: TransactionFilters['kind']; label: string }[] = [
  { value: undefined, label: 'Все' },
  { value: 'expense', label: 'Расходы' },
  { value: 'income', label: 'Доходы' },
]

function groupByDate(items: Transaction[]) {
  const groups = new Map<string, Transaction[]>()
  for (const t of items) groups.set(t.date, [...(groups.get(t.date) ?? []), t])
  return [...groups.entries()]
}

export function TransactionsPage() {
  const [q, setQ] = useState('')
  const [kind, setKind] = useState<TransactionFilters['kind']>()
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [adding, setAdding] = useState(false)
  const deferredQ = useDeferredValue(q)

  const query = useTransactions({ q: deferredQ, kind })
  const categories = useCategoryMap()
  const { data: accounts = [] } = useAccounts()
  const accountNames = new Map(accounts.map((a) => [a.id, a.name]))

  const items = useMemo(() => query.data?.pages.flatMap((p) => p.items) ?? [], [query.data])
  const groups = groupByDate(items)

  return (
    <>
      <PageHeader
        title="Операции"
        action={
          <Button size="icon" aria-label="Добавить операцию" onClick={() => setAdding(true)}>
            <Plus className="h-5 w-5" />
          </Button>
        }
      />

      <div className="sticky top-0 z-10 -mx-4 space-y-2 bg-slate-50 px-4 pb-3">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по описанию" className="pl-10" />
        </div>
        <div className="flex gap-2">
          {KINDS.map((k) => (
            <button
              key={k.label}
              onClick={() => setKind(k.value)}
              className={cn(
                'rounded-full px-3 py-1 text-sm',
                kind === k.value ? 'bg-brand-600 text-white' : 'bg-white text-slate-600',
              )}
            >
              {k.label}
            </button>
          ))}
        </div>
      </div>

      {query.isLoading && <PageLoader />}
      {query.error && <ErrorMessage error={query.error} />}
      {query.isSuccess && items.length === 0 && (
        <EmptyState icon={<Wallet className="h-8 w-8" />} title="Операций пока нет">
          <Button className="mt-2" onClick={() => setAdding(true)}>
            Добавить первую операцию
          </Button>
        </EmptyState>
      )}

      <div className="space-y-4">
        {groups.map(([date, txs]) => {
          const dayTotal = txs.reduce((s, t) => s + (t.amount < 0 ? t.amount : 0), 0)
          return (
            <section key={date}>
              <div className="mb-1 flex justify-between px-1 text-sm text-slate-500">
                <span>{formatDate(date, { day: 'numeric', month: 'long', weekday: 'short' })}</span>
                {dayTotal < 0 && <span>{formatMoney(dayTotal)}</span>}
              </div>
              <ul className="divide-y divide-slate-100 rounded-2xl bg-white shadow-sm">
                {txs.map((t) => {
                  const cat = t.category_id ? categories.get(t.category_id) : undefined
                  return (
                    <li key={t.id}>
                      <button className="flex w-full items-center gap-3 p-3 text-left" onClick={() => setEditing(t)}>
                        <CategoryIcon category={cat} />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium">{t.description || cat?.name || 'Без описания'}</span>
                          <span className="block truncate text-xs text-slate-500">
                            {cat?.name ?? 'Без категории'} · {accountNames.get(t.account_id)}
                          </span>
                        </span>
                        <span className={cn('font-semibold tabular-nums', t.amount > 0 && 'text-emerald-600')}>
                          {formatMoney(t.amount, { sign: true })}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </section>
          )
        })}
      </div>

      {query.hasNextPage && (
        <Button
          variant="secondary"
          className="mt-4 w-full"
          disabled={query.isFetchingNextPage}
          onClick={() => query.fetchNextPage()}
        >
          Показать ещё
        </Button>
      )}

      <Sheet open={adding} onClose={() => setAdding(false)} title="Новая операция">
        <TransactionForm onDone={() => setAdding(false)} />
      </Sheet>
      <Sheet open={editing !== null} onClose={() => setEditing(null)} title="Операция">
        {editing && <TransactionForm key={editing.id} transaction={editing} onDone={() => setEditing(null)} />}
      </Sheet>
    </>
  )
}
