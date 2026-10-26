import { Lock, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useCategories } from '@/api/hooks'
import type { Horizon } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { PageHeader } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { EmptyState, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { track } from '@/lib/track'
import { cn, formatDate, formatMoney } from '@/lib/utils'

import { useForecast, useStrategies } from './api'
import { BalanceChart } from './BalanceChart'
import { RiskBadge } from './RiskBadge'
import { UpcomingList } from './UpcomingList'
import { useIsPremium, usePlanHorizon } from '@/features/subscription/api'
import { useSettings } from '@/store/settings'

export function ForecastPage() {
  const navigate = useNavigate()
  const planHorizon = usePlanHorizon()
  const isPremium = useIsPremium()
  const [chosen, setHorizon] = useState<Horizon>()
  const horizon = chosen ?? planHorizon
  const forecast = useForecast(horizon)
  useEffect(() => track('forecast_viewed'), [])
  const strategy = useSettings((s) => s.strategy)
  const { data: strategies } = useStrategies()
  const { data: categories = [] } = useCategories()
  const bySlug = new Map(categories.map((c) => [c.slug, c]))
  const f = forecast.data
  const strategyTitle = strategies?.find((s) => s.name === strategy)?.title

  return (
    <>
      <PageHeader title="Прогноз" />
      <div className="mb-4 grid grid-cols-2 gap-1 rounded-xl bg-white p-1 shadow-sm">
        {(['week', 'month'] as const).map((h) => (
          <button
            key={h}
            onClick={() => (h === 'month' && !isPremium ? navigate('/premium?from=forecast') : setHorizon(h))}
            className={cn(
              'flex items-center justify-center gap-1 rounded-lg py-2 text-sm font-medium',
              horizon === h ? 'bg-brand-600 text-white' : 'text-slate-600',
            )}
          >
            {h === 'week' ? 'Неделя' : 'Месяц'}
            {h === 'month' && !isPremium && <Lock className="h-3.5 w-3.5" aria-label="Premium" />}
          </button>
        ))}
      </div>

      {(forecast.isLoading || !horizon) && <PageLoader />}
      {forecast.error && <NoForecast error={forecast.error} />}
      {f && (
        <div className="space-y-4">
          <Card className="space-y-3">
            <div>
              <CardTitle>Баланс до {formatDate(f.period_end)}</CardTitle>
              <p className="mt-1 text-sm text-slate-500">
                Сейчас {formatMoney(f.current_balance)} → к концу периода ≈{' '}
                <b className="text-slate-900">{formatMoney(f.expected_balance_end)}</b>
              </p>
            </div>
            <RiskBadge risk={f.cash_gap.risk} />
            {f.cash_gap.first_negative_date && f.cash_gap.probability >= 0.15 && (
              <p className="text-sm text-slate-600">
                Возможный уход в минус — около <b>{formatDate(f.cash_gap.first_negative_date)}</b> (вероятность{' '}
                {Math.round(f.cash_gap.probability * 100)}%)
              </p>
            )}
            <BalanceChart forecast={f} />
            <p className="text-xs text-slate-500">Линия — ожидаемый баланс, заливка — 80% возможных сценариев.</p>
          </Card>

          <div className="grid grid-cols-2 gap-3">
            <Card>
              <CardTitle>Потратите</CardTitle>
              <p className="mt-1 text-lg font-bold tabular-nums">≈ {formatMoney(f.expected_expense)}</p>
              <p className="text-xs text-slate-500 tabular-nums">
                {formatMoney(f.expected_expense_p10)} – {formatMoney(f.expected_expense_p90)}
              </p>
            </Card>
            <Card>
              <CardTitle>Поступит</CardTitle>
              <p className="mt-1 text-lg font-bold tabular-nums">≈ {formatMoney(f.expected_income)}</p>
              <p className="text-xs text-slate-500">по регулярным доходам</p>
            </Card>
          </div>

          <Card>
            <CardTitle className="mb-2">Прогноз по категориям</CardTitle>
            <ul className="space-y-2">
              {f.by_category
                .filter((c) => c.expected >= 1)
                .slice(0, 10)
                .map((c) => (
                  <li key={c.category} className="flex items-center gap-3">
                    <CategoryIcon category={bySlug.get(c.category)} size="sm" />
                    <span className="min-w-0 flex-1 truncate text-sm">{bySlug.get(c.category)?.name ?? c.category}</span>
                    {c.recurring > 0 && <span className="text-xs text-slate-400">регулярно</span>}
                    <span className="text-sm font-semibold tabular-nums">{formatMoney(c.expected)}</span>
                  </li>
                ))}
            </ul>
          </Card>

          <Card>
            <CardTitle className="mb-1">Ожидаемые платежи и поступления</CardTitle>
            <UpcomingList items={f.upcoming} />
          </Card>

          <Card className="text-sm text-slate-600">
            <CardTitle className="mb-1 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" /> Как считали
            </CardTitle>
            <p>{f.explanation}</p>
            <p className="mt-2 text-xs text-slate-400">
              Модель: {strategyTitle ?? strategy}.{' '}
              <Link to="/experiments" className="text-brand-600 underline">
                Сменить и сравнить модели
              </Link>
            </p>
          </Card>
        </div>
      )}
    </>
  )
}

export function NoForecast({ error }: { error: unknown }) {
  const status = (error as { status?: number }).status
  if (status !== 409) return <ErrorMessage error={error} />
  return (
    <EmptyState icon={<TrendingUp className="h-8 w-8" />} title="Пока не из чего строить прогноз">
      <p className="text-sm">Подключите банк или загрузите выписку — прогноз появится сразу.</p>
      <Link to="/connect-bank">
        <Button className="mt-2">Подключить банк</Button>
      </Link>
    </EmptyState>
  )
}
