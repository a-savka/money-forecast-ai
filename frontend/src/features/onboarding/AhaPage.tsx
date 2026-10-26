import { Clock, Sparkles, Wallet } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { PageLoader } from '@/components/ui/feedback'
import { NoForecast } from '@/features/forecast/ForecastPage'
import { RiskBadge } from '@/features/forecast/RiskBadge'
import { useForecast } from '@/features/forecast/api'
import { RecommendationCard } from '@/features/recommendations/RecommendationCard'
import { useRecommendations } from '@/features/recommendations/api'
import { usePlanHorizon } from '@/features/subscription/api'
import { clearOnboardingStart, onboardingElapsed, track } from '@/lib/track'
import { formatDate, formatMoney } from '@/lib/utils'
import { useSettings } from '@/store/settings'

function formatDuration(s: number) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** Aha-момент: первый прогноз сразу после загрузки данных. */
export function AhaPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const horizon = usePlanHorizon()
  const forecast = useForecast(horizon)
  const recs = useRecommendations().data?.items ?? []
  const goal = useSettings((s) => s.goal)
  // Время от входа до экрана прогноза; событие отправляем один раз, когда прогноз показан
  const [elapsed] = useState(onboardingElapsed)
  const tracked = useRef(false)
  const f = forecast.data

  useEffect(() => {
    if (!f || tracked.current) return
    tracked.current = true
    const seconds = onboardingElapsed()
    if (seconds !== null) {
      track('onboarding_done', { seconds, source: params.get('source'), goal })
      clearOnboardingStart()
    }
  }, [f, params, goal])

  return (
    <div className="pt-safe mx-auto min-h-full max-w-md space-y-4 bg-slate-50 px-4 pb-10">
      <div className="flex gap-1 py-4" aria-label="Шаг 3 из 3">
        {[1, 2, 3].map((i) => (
          <span key={i} className="h-1.5 flex-1 rounded-full bg-brand-600" />
        ))}
      </div>
      <h1 className="flex items-center gap-2 text-2xl font-bold">
        <Sparkles className="h-6 w-6 text-brand-600" /> Ваш первый прогноз
      </h1>

      {(forecast.isLoading || !horizon) && <PageLoader />}
      {forecast.error && <NoForecast error={forecast.error} />}
      {f && (
        <>
          <Card className="space-y-3 bg-gradient-to-br from-brand-600 to-brand-700 text-white">
            <p className="text-brand-100">До {formatDate(f.period_end)} вы потратите</p>
            <p className="text-4xl font-bold tabular-nums">≈ {formatMoney(f.expected_expense)}</p>
            <RiskBadge risk={f.cash_gap.risk} className="bg-white/95" />
            {f.cash_gap.first_negative_date && f.cash_gap.probability >= 0.15 && (
              <p className="text-sm text-brand-100">
                Деньги могут закончиться около {formatDate(f.cash_gap.first_negative_date)}
              </p>
            )}
          </Card>

          <Card className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <Wallet className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>Чтобы уложиться, тратьте в день не больше</CardTitle>
              <p className="text-xl font-bold tabular-nums">{formatMoney(f.safe_to_spend_per_day)}</p>
              {f.safe_to_spend_per_day === 0 && (
                <p className="text-xs text-slate-500">Свободных денег до поступлений нет — посмотрите совет ниже</p>
              )}
            </div>
          </Card>

          {recs.length > 0 && (
            <Card>
              <CardTitle>Первый совет</CardTitle>
              <ul>
                <RecommendationCard rec={recs[0]} />
              </ul>
            </Card>
          )}

          {elapsed !== null && (
            <p className="flex items-center justify-center gap-1 text-sm text-slate-500">
              <Clock className="h-4 w-4" /> Прогноз готов за {formatDuration(elapsed)}
            </p>
          )}
          <Button className="w-full" size="lg" onClick={() => navigate('/', { replace: true })}>
            Перейти на главную
          </Button>
        </>
      )}
    </div>
  )
}
