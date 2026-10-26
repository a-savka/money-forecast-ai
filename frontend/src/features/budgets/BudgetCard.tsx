import { AlertTriangle, CheckCircle2, OctagonAlert } from 'lucide-react'

import type { BudgetStatus, Category } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { cn, formatMoney } from '@/lib/utils'

const STATUS = {
  ok: { icon: CheckCircle2, label: 'В пределах лимита', text: 'text-emerald-700', bar: 'bg-emerald-500' },
  warning: { icon: AlertTriangle, label: 'Может не хватить', text: 'text-amber-700', bar: 'bg-amber-500' },
  over: { icon: OctagonAlert, label: 'Лимит превышен', text: 'text-red-700', bar: 'bg-red-500' },
} as const

function inDays(days: number) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
}

function forecastText(b: BudgetStatus) {
  if (b.status === 'over') return `Перерасход ${formatMoney(-b.remaining)}`
  if (b.exhausted_in_days == null) return 'Трат в этой категории пока нет'
  if (b.exhausted_in_days < b.days_left_in_month) {
    return b.exhausted_in_days === 0
      ? 'Закончится уже сегодня'
      : `Закончится через ${b.exhausted_in_days} дн. — около ${inDays(b.exhausted_in_days)}`
  }
  return `Хватит до конца месяца, останется ≈ ${formatMoney(b.limit - b.projected)}`
}

export function BudgetCard({ budget: b, category, compact }: { budget: BudgetStatus; category?: Category; compact?: boolean }) {
  const st = STATUS[b.status]
  const Icon = st.icon
  const share = Math.min(1, b.spent / b.limit)
  const projectedShare = Math.min(1, b.projected / b.limit)
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <CategoryIcon category={category} size="sm" />
        <span className="min-w-0 flex-1 truncate font-medium">{category?.name ?? 'Категория'}</span>
        <span className="text-sm tabular-nums">
          <b>{formatMoney(b.spent)}</b> <span className="text-slate-400">из {formatMoney(b.limit)}</span>
        </span>
      </div>
      <div
        className="relative h-2 overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-valuenow={Math.round(share * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Потрачено ${Math.round(share * 100)}% лимита`}
      >
        {/* Прогноз к концу месяца — светлая часть полосы */}
        <div className={cn('absolute inset-y-0 left-0 rounded-full opacity-25', st.bar)} style={{ width: `${projectedShare * 100}%` }} />
        <div className={cn('absolute inset-y-0 left-0 rounded-full', st.bar)} style={{ width: `${share * 100}%` }} />
      </div>
      <p className={cn('flex items-center gap-1 text-xs', st.text)}>
        <Icon className="h-3.5 w-3.5 shrink-0" />
        <span>
          {!compact && <b>{st.label}. </b>}
          {forecastText(b)}
        </span>
      </p>
    </div>
  )
}
