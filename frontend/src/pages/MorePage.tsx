import { ChevronRight, Crown, FlaskConical, LogOut } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useSubscription } from '@/features/subscription/api'
import { useSession } from '@/store/session'

export function MorePage() {
  const { user, logout } = useSession()
  const navigate = useNavigate()
  const { data: sub } = useSubscription()
  const planLabel =
    sub?.plan === 'premium'
      ? 'Premium активен'
      : sub?.plan === 'trial'
        ? `Пробный период: ещё ${sub.trial_days_left} дн.`
        : 'Free · прогноз на неделю'
  return (
    <>
      <PageHeader title="Ещё" />
      <Card className="mb-4">
        <p className="font-semibold">{user?.name}</p>
        <p className="text-sm text-slate-500">{user?.email}</p>
      </Card>
      <Card className="mb-4 p-0">
        <Link to="/premium" className="flex items-center gap-3 p-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 text-amber-500">
            <Crown className="h-5 w-5" />
          </span>
          <span className="flex-1">
            <span className="block font-medium">Подписка</span>
            <span className="block text-sm text-slate-500">{planLabel}</span>
          </span>
          <ChevronRight className="h-5 w-5 text-slate-400" />
        </Link>
      </Card>
      <Card className="mb-4 p-0">
        <Link to="/experiments" className="flex items-center gap-3 p-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-600">
            <FlaskConical className="h-5 w-5" />
          </span>
          <span className="flex-1">
            <span className="block font-medium">Эксперименты</span>
            <span className="block text-sm text-slate-500">Стратегии прогноза H0–H3 и бэктест</span>
          </span>
          <ChevronRight className="h-5 w-5 text-slate-400" />
        </Link>
      </Card>
      <Button
        variant="secondary"
        className="w-full"
        onClick={() => {
          logout()
          navigate('/login')
        }}
      >
        <LogOut className="h-4 w-4" /> Выйти
      </Button>
    </>
  )
}
