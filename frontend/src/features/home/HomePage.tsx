import { CalendarClock, ChevronRight, Wallet } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAccounts } from '@/api/hooks'
import { Card, CardTitle } from '@/components/ui/card'
import { PageLoader } from '@/components/ui/feedback'
import { NoForecast } from '@/features/forecast/ForecastPage'
import { RiskBadge } from '@/features/forecast/RiskBadge'
import { UpcomingList } from '@/features/forecast/UpcomingList'
import { useForecast } from '@/features/forecast/api'
import { formatDate, formatMoney } from '@/lib/utils'
import { useSession } from '@/store/session'

export function HomePage() {
  const user = useSession((s) => s.user)
  const forecast = useForecast('month')
  const { data: accounts = [] } = useAccounts()
  const f = forecast.data

  return (
    <div className="space-y-4 pt-4">
      <header>
        <p className="text-sm text-slate-500">Привет, {user?.name ?? 'друг'} 👋</p>
        <h1 className="text-2xl font-bold">Ваш прогноз</h1>
      </header>

      {forecast.isLoading && <PageLoader />}
      {forecast.error && <NoForecast error={forecast.error} />}

      {f && (
        <>
          <Link to="/forecast" className="block">
            <Card className="space-y-3 bg-gradient-to-br from-brand-600 to-brand-700 text-white">
              <p className="text-brand-100">До {formatDate(f.period_end)} вы потратите</p>
              <p className="text-4xl font-bold tabular-nums">≈ {formatMoney(f.expected_expense)}</p>
              <RiskBadge risk={f.cash_gap.risk} className="bg-white/95" />
              {f.cash_gap.first_negative_date && f.cash_gap.probability >= 0.15 && (
                <p className="text-sm text-brand-100">
                  Деньги могут закончиться около {formatDate(f.cash_gap.first_negative_date)}
                </p>
              )}
              <div className="flex items-center justify-between text-sm text-brand-100">
                <span>
                  Баланс к концу периода ≈ <b className="text-white">{formatMoney(f.expected_balance_end)}</b>
                </span>
                <ChevronRight className="h-5 w-5" />
              </div>
            </Card>
          </Link>

          <Card className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <Wallet className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>Можно тратить в день</CardTitle>
              <p className="text-xl font-bold tabular-nums">{formatMoney(f.safe_to_spend_per_day)}</p>
            </div>
          </Card>

          <Card>
            <CardTitle className="mb-1 flex items-center gap-1">
              <CalendarClock className="h-4 w-4" /> Ближайшие платежи
            </CardTitle>
            <UpcomingList items={f.upcoming} limit={4} />
          </Card>
        </>
      )}

      {accounts.length > 0 && (
        <Card>
          <CardTitle className="mb-2">Счета</CardTitle>
          <ul className="space-y-1">
            {accounts.map((a) => (
              <li key={a.id} className="flex justify-between text-sm">
                <span>
                  {a.name} <span className="text-slate-400">{a.bank_name}</span>
                </span>
                <span className="font-semibold tabular-nums">{formatMoney(a.balance)}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
