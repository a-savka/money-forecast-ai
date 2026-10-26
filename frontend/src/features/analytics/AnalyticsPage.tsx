import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, PieChart } from 'lucide-react'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api, unwrap } from '@/api/client'
import { useCategoryMap } from '@/api/hooks'
import type { MonthPoint, MonthSummary } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { PageHeader } from '@/components/layout/AppLayout'
import { Card, CardTitle } from '@/components/ui/card'
import { EmptyState, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { cn, formatMoney } from '@/lib/utils'

// Палитра проверена валидатором dataviz (категориальные слоты «aqua» и «blue»)
const SERIES = { income: '#1baf7a', expense: '#2a78d6' }

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function shiftMonth(month: string, delta: number) {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function monthTitle(month: string, opts: Intl.DateTimeFormatOptions = { month: 'long', year: 'numeric' }) {
  const [y, m] = month.split('-').map(Number)
  const s = new Date(y, m - 1, 1).toLocaleDateString('ru-RU', opts)
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function AnalyticsPage() {
  const [month, setMonth] = useState(currentMonth())
  const isCurrent = month === currentMonth()

  const summary = useQuery({
    queryKey: ['analytics', 'summary', month],
    queryFn: () => unwrap<MonthSummary>(api.GET('/analytics/summary', { params: { query: { month } } })),
    placeholderData: keepPreviousData,
  })
  const dyn = useQuery({
    queryKey: ['analytics', 'dynamics'],
    queryFn: () => unwrap<MonthPoint[]>(api.GET('/analytics/dynamics', { params: { query: { months: 6 } } })),
  })

  return (
    <>
      <PageHeader title="Аналитика" />
      <div className="mb-4 flex items-center justify-between rounded-2xl bg-white p-2 shadow-sm">
        <button aria-label="Предыдущий месяц" className="rounded-full p-2 hover:bg-slate-100" onClick={() => setMonth(shiftMonth(month, -1))}>
          <ChevronLeft className="h-5 w-5" />
        </button>
        <span className="font-semibold">{monthTitle(month)}</span>
        <button
          aria-label="Следующий месяц"
          className="rounded-full p-2 hover:bg-slate-100 disabled:opacity-30"
          disabled={isCurrent}
          onClick={() => setMonth(shiftMonth(month, 1))}
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {summary.isLoading && <PageLoader />}
      {summary.error && <ErrorMessage error={summary.error} />}
      {summary.data && <Summary data={summary.data} isCurrent={isCurrent} />}

      {dyn.data?.some((p) => p.income > 0 || p.expense > 0) && (
        <Card className="mt-4">
          <CardTitle>Доходы и расходы за 6 месяцев</CardTitle>
          <Dynamics points={dyn.data} />
        </Card>
      )}
    </>
  )
}

function Summary({ data, isCurrent }: { data: MonthSummary; isCurrent: boolean }) {
  const categories = useCategoryMap()
  const delta = data.prev_expense ? (data.expense - data.prev_expense) / data.prev_expense : 0

  if (data.expense === 0 && data.income === 0)
    return <EmptyState icon={<PieChart className="h-8 w-8" />} title="За этот месяц операций нет" />

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Card>
          <CardTitle>Расходы</CardTitle>
          <p className="mt-1 text-xl font-bold tabular-nums">{formatMoney(data.expense)}</p>
          {data.prev_expense > 0 && (
            <p className={cn('text-xs', delta > 0 ? 'text-red-600' : 'text-emerald-600')}>
              {delta > 0 ? '▲' : '▼'} {Math.abs(Math.round(delta * 100))}%{' '}
              <span className="text-slate-500">{isCurrent ? `к ${data.days_elapsed} дням прошлого` : 'к прошлому месяцу'}</span>
            </p>
          )}
        </Card>
        <Card>
          <CardTitle>Доходы</CardTitle>
          <p className="mt-1 text-xl font-bold tabular-nums">{formatMoney(data.income)}</p>
          <p className="text-xs text-slate-500">
            Остаток: <span className="font-medium text-slate-700">{formatMoney(data.net, { sign: true })}</span>
          </p>
        </Card>
      </div>

      <Card>
        <CardTitle className="mb-3">Куда уходят деньги</CardTitle>
        <ul className="space-y-3">
          {data.by_category.map((c) => {
            const cat = categories.get(c.category_id)
            const change = c.prev_amount ? (c.amount - c.prev_amount) / c.prev_amount : null
            return (
              <li key={c.category_id} className="flex items-center gap-3">
                <CategoryIcon category={cat} size="sm" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="truncate font-medium">{cat?.name ?? 'Без категории'}</span>
                    <span className="font-semibold tabular-nums">{formatMoney(c.amount)}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <div className="h-1.5 flex-1 rounded-full bg-slate-100">
                      <div
                        className="h-1.5 rounded-full"
                        style={{ width: `${Math.max(2, c.share * 100)}%`, backgroundColor: cat?.color ?? '#94a3b8' }}
                      />
                    </div>
                    <span className="w-9 text-right text-xs text-slate-500 tabular-nums">{Math.round(c.share * 100)}%</span>
                    <span
                      className={cn(
                        'w-12 text-right text-xs tabular-nums',
                        change === null ? 'text-slate-400' : change > 0.1 ? 'text-red-600' : change < -0.1 ? 'text-emerald-600' : 'text-slate-500',
                      )}
                      title="Изменение к прошлому месяцу"
                    >
                      {change === null ? 'новое' : `${change > 0 ? '+' : ''}${Math.round(change * 100)}%`}
                    </span>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      </Card>
    </div>
  )
}

const compact = new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 0 })

function Dynamics({ points }: { points: MonthPoint[] }) {
  const data = points.map((p) => ({ ...p, label: monthTitle(p.month, { month: 'short' }).replace('.', '') }))
  return (
    <>
      <div className="mt-2 flex gap-4 text-xs text-slate-600">
        {(['income', 'expense'] as const).map((k) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: SERIES[k] }} />
            {k === 'income' ? 'Доходы' : 'Расходы'}
          </span>
        ))}
      </div>
      <div className="mt-2 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={2} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis width={56} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => compact.format(v)} />
            <Tooltip
              cursor={{ fill: '#f1f5f9' }}
              formatter={(v, name) => [formatMoney(Number(v)), name === 'income' ? 'Доходы' : 'Расходы']}
              labelStyle={{ fontWeight: 600 }}
              contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
            />
            <Bar dataKey="income" fill={SERIES.income} radius={[4, 4, 0, 0]} maxBarSize={18} />
            <Bar dataKey="expense" fill={SERIES.expense} radius={[4, 4, 0, 0]} maxBarSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {/* Табличное представление: значения без зависимости от цвета */}
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-slate-500">Таблица</summary>
        <table className="mt-2 w-full text-right tabular-nums">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="text-left font-normal">Месяц</th>
              <th className="font-normal">Доходы</th>
              <th className="font-normal">Расходы</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.month}>
                <td className="text-left">{monthTitle(p.month)}</td>
                <td>{formatMoney(p.income)}</td>
                <td>{formatMoney(p.expense)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  )
}
