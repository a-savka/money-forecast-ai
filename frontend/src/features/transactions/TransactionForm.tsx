import { Trash2 } from 'lucide-react'
import { useState } from 'react'

import { useAccounts, useCategories, useCreateTransaction, useDeleteTransaction, useUpdateTransaction } from '@/api/hooks'
import type { Transaction } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { Button } from '@/components/ui/button'
import { ErrorMessage } from '@/components/ui/feedback'
import { Input, Label, Select } from '@/components/ui/input'
import { cn, todayIso } from '@/lib/utils'

type Kind = 'expense' | 'income'

export interface TransactionDraft {
  amount?: number
  date?: string
  description?: string
  category_id?: number | null
}

export function TransactionForm({
  transaction,
  draft,
  onDone,
}: {
  transaction?: Transaction
  draft?: TransactionDraft
  onDone: () => void
}) {
  const initial = transaction ?? draft
  const { data: categories = [] } = useCategories()
  const { data: accounts = [] } = useAccounts()
  const [kind, setKind] = useState<Kind>((initial?.amount ?? -1) > 0 ? 'income' : 'expense')
  const [amount, setAmount] = useState(initial?.amount ? String(Math.abs(initial.amount)) : '')
  const [date, setDate] = useState(initial?.date ?? todayIso())
  const [description, setDescription] = useState(initial?.description ?? '')
  const [categoryId, setCategoryId] = useState<number | null>(initial?.category_id ?? null)
  const [accountId, setAccountId] = useState<number | undefined>(transaction?.account_id)

  const create = useCreateTransaction()
  const update = useUpdateTransaction()
  const remove = useDeleteTransaction()
  const pending = create.isPending || update.isPending || remove.isPending
  const error = create.error || update.error || remove.error

  const visible = categories.filter((c) => c.kind === kind)
  const value = Number(amount.replace(',', '.'))
  const valid = value > 0 && Boolean(date)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return
    const signed = kind === 'expense' ? -value : value
    const body = {
      amount: signed,
      date,
      description,
      category_id: categoryId,
      account_id: accountId ?? accounts[0]?.id,
    }
    if (transaction) await update.mutateAsync({ id: transaction.id, body })
    else await create.mutateAsync(body)
    onDone()
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1">
        {(['expense', 'income'] as const).map((k) => (
          <button
            type="button"
            key={k}
            onClick={() => {
              setKind(k)
              setCategoryId(null)
            }}
            className={cn('rounded-lg py-2 text-sm font-medium', kind === k ? 'bg-white shadow-sm' : 'text-slate-500')}
          >
            {k === 'expense' ? 'Расход' : 'Доход'}
          </button>
        ))}
      </div>

      <div>
        <Label htmlFor="amount">Сумма, ₽</Label>
        <Input
          id="amount"
          inputMode="decimal"
          autoFocus={!transaction}
          value={amount}
          onChange={(e) => setAmount(e.target.value.replace(/[^\d.,]/g, ''))}
          placeholder="0"
          className="text-2xl font-semibold"
        />
      </div>

      <div>
        <Label>Категория</Label>
        <div className="grid grid-cols-4 gap-2">
          {visible.map((c) => (
            <button
              type="button"
              key={c.id}
              onClick={() => setCategoryId(c.id)}
              className={cn(
                'flex flex-col items-center gap-1 rounded-xl border p-2 text-[11px] leading-tight',
                categoryId === c.id ? 'border-brand-500 bg-brand-50' : 'border-transparent',
              )}
            >
              <CategoryIcon category={c} size="sm" />
              {c.name}
            </button>
          ))}
        </div>
      </div>

      <div>
        <Label htmlFor="description">Описание</Label>
        <Input id="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Например, Пятёрочка" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="date">Дата</Label>
          <Input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="account">Счёт</Label>
          <Select
            id="account"
            value={accountId ?? accounts[0]?.id ?? ''}
            onChange={(e) => setAccountId(Number(e.target.value))}
          >
            {accounts.length === 0 && <option value="">Наличные</option>}
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {error && <ErrorMessage error={error} />}

      <div className="flex gap-2">
        {transaction && (
          <Button
            type="button"
            variant="secondary"
            size="icon"
            className="h-11 w-11 text-red-600"
            aria-label="Удалить"
            disabled={pending}
            onClick={async () => {
              await remove.mutateAsync(transaction.id)
              onDone()
            }}
          >
            <Trash2 className="h-5 w-5" />
          </Button>
        )}
        <Button type="submit" className="flex-1" disabled={!valid || pending}>
          {transaction ? 'Сохранить' : 'Добавить'}
        </Button>
      </div>
    </form>
  )
}
