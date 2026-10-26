import { useCategories } from '@/api/hooks'
import type { ForecastResult } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { cn, formatDate, formatMoney } from '@/lib/utils'

export function UpcomingList({ items, limit }: { items: ForecastResult['upcoming']; limit?: number }) {
  const { data: categories = [] } = useCategories()
  const bySlug = new Map(categories.map((c) => [c.slug, c]))
  const shown = limit ? items.slice(0, limit) : items
  if (shown.length === 0) return <p className="text-sm text-slate-500">Регулярных платежей до конца периода нет</p>
  return (
    <ul className="divide-y divide-slate-100">
      {shown.map((u, i) => (
        <li key={`${u.date}-${u.name}-${i}`} className="flex items-center gap-3 py-2">
          <CategoryIcon category={bySlug.get(u.category)} size="sm" />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">{u.name}</span>
            <span className="block text-xs text-slate-500">{formatDate(u.date, { day: 'numeric', month: 'long', weekday: 'short' })}</span>
          </span>
          <span className={cn('text-sm font-semibold tabular-nums', u.amount > 0 && 'text-emerald-600')}>
            {formatMoney(u.amount, { sign: true })}
          </span>
        </li>
      ))}
    </ul>
  )
}
