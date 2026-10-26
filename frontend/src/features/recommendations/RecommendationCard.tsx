import { AlertTriangle, PiggyBank, Repeat, Sparkles, TrendingUp } from 'lucide-react'

import type { Recommendation } from '@/api/types'
import { useCategories } from '@/api/hooks'
import { cn, formatMoney } from '@/lib/utils'

const TYPES = {
  cash_gap: { icon: AlertTriangle, tone: 'bg-red-50 text-red-600', label: 'Кассовый разрыв' },
  category_growth: { icon: TrendingUp, tone: 'bg-amber-50 text-amber-600', label: 'Рост трат' },
  save: { icon: PiggyBank, tone: 'bg-emerald-50 text-emerald-600', label: 'Накопления' },
  subscriptions: { icon: Repeat, tone: 'bg-brand-50 text-brand-600', label: 'Подписки' },
} as const

export function RecommendationCard({ rec, compact }: { rec: Recommendation; compact?: boolean }) {
  const { data: categories = [] } = useCategories()
  const meta = TYPES[rec.type as keyof typeof TYPES] ?? TYPES.subscriptions
  const Icon = meta.icon
  const category = categories.find((c) => c.slug === rec.category)

  return (
    <li className="flex gap-3 py-3">
      <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-full', meta.tone)}>
        <Icon className="h-4 w-4" aria-label={meta.label} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-medium leading-snug">{rec.title}</p>
        {!compact && <p className="mt-1 text-sm text-slate-600">{rec.text}</p>}
        <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
          {category && <span>{category.name}</span>}
          {rec.amount_effect > 0 && rec.id !== 'gap-topup' && (
            <span className="font-semibold text-emerald-700">+{formatMoney(rec.amount_effect)} к балансу</span>
          )}
          {rec.source === 'llm' && (
            <span className="inline-flex items-center gap-0.5">
              <Sparkles className="h-3 w-3" /> ИИ
            </span>
          )}
        </div>
      </div>
    </li>
  )
}
