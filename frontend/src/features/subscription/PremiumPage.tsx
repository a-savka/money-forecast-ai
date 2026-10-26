import { ArrowLeft, Check, Crown, Minus } from 'lucide-react'
import { useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { track } from '@/lib/track'
import { formatDate, formatMoney } from '@/lib/utils'

import { useChangeSubscription, useSubscription } from './api'

const FEATURES: { title: string; free: boolean | string; premium: boolean | string }[] = [
  { title: 'Учёт операций, импорт выписок и чеков', free: true, premium: true },
  { title: 'Прогноз трат и баланса', free: 'неделя', premium: 'месяц' },
  { title: 'Предупреждение о кассовом разрыве', free: 'за 7 дней', premium: 'за месяц' },
  { title: 'Советы ИИ по экономии', free: true, premium: true },
  { title: 'Семейный бюджет', free: false, premium: true },
  { title: 'Лимиты по категориям', free: '1 лимит', premium: 'без огранич.' },
]

function Cell({ value }: { value: boolean | string }) {
  if (typeof value === 'string') return <span className="text-xs font-medium">{value}</span>
  return value ? (
    <Check className="mx-auto h-4 w-4 text-emerald-600" aria-label="есть" />
  ) : (
    <Minus className="mx-auto h-4 w-4 text-slate-300" aria-label="нет" />
  )
}

export function PremiumPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const back = params.get('from') === 'forecast' ? '/forecast' : '/more'
  const { data: sub, isLoading } = useSubscription()
  const change = useChangeSubscription()

  useEffect(() => track('paywall_shown', { from: params.get('from') }), [params])

  const act = (action: 'start_trial' | 'upgrade' | 'cancel') =>
    change.mutate(action, { onSuccess: () => action !== 'cancel' && navigate(back) })

  return (
    <div className="mx-auto min-h-full max-w-md space-y-4 bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to={back} className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">MoneyForecast Premium</h1>
      </header>

      <Card className="space-y-2 bg-gradient-to-br from-amber-400 to-orange-500 text-white">
        <Crown className="h-8 w-8" />
        <p className="text-xl font-bold">Знайте заранее, хватит ли денег до конца месяца</p>
        <p className="text-sm text-amber-50">
          Прогноз на месяц вперёд, раннее предупреждение о кассовом разрыве, семейный бюджет и лимиты.
        </p>
      </Card>

      {isLoading && <PageLoader />}
      {sub && (
        <>
          <Card className="p-0">
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-500">
                <tr>
                  <th className="p-3 text-left font-medium">Возможности</th>
                  <th className="w-20 p-3 font-medium">Free</th>
                  <th className="w-20 p-3 font-medium text-amber-600">Premium</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {FEATURES.map((f) => (
                  <tr key={f.title}>
                    <td className="p-3">{f.title}</td>
                    <td className="p-3 text-center">
                      <Cell value={f.free} />
                    </td>
                    <td className="p-3 text-center">
                      <Cell value={f.premium} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {sub.plan === 'free' ? (
            <div className="space-y-2">
              {sub.can_start_trial && (
                <Button className="w-full" size="lg" onClick={() => act('start_trial')} disabled={change.isPending}>
                  Попробовать 7 дней бесплатно
                </Button>
              )}
              <Button
                variant={sub.can_start_trial ? 'secondary' : 'primary'}
                className="w-full"
                onClick={() => act('upgrade')}
                disabled={change.isPending}
              >
                Оформить за {formatMoney(sub.price_month)} в месяц
              </Button>
              <p className="text-center text-xs text-slate-500">
                или {formatMoney(sub.price_year)} в год. Демо-версия: оплата не списывается.
              </p>
            </div>
          ) : (
            <Card className="space-y-3">
              <p className="font-medium">
                {sub.plan === 'trial'
                  ? `Пробный период: осталось ${sub.trial_days_left} дн. (до ${formatDate(sub.trial_until!)})`
                  : 'Premium активен'}
              </p>
              <div className="flex gap-2">
                {sub.plan === 'trial' && (
                  <Button className="flex-1" onClick={() => act('upgrade')} disabled={change.isPending}>
                    Оформить
                  </Button>
                )}
                <Button variant="secondary" className="flex-1" onClick={() => act('cancel')} disabled={change.isPending}>
                  Отменить
                </Button>
              </div>
            </Card>
          )}
          {change.error && <ErrorMessage error={change.error} />}
        </>
      )}
    </div>
  )
}
