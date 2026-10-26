import { ChevronRight, Crown, FlaskConical, LogOut, Users, type LucideIcon } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useFamily } from '@/features/family/api'
import { useSubscription } from '@/features/subscription/api'
import { useSession } from '@/store/session'

interface MenuItem {
  to: string
  icon: LucideIcon
  tone: string
  title: string
  hint: string
}

export function MorePage() {
  const { user, logout } = useSession()
  const navigate = useNavigate()
  const { data: sub } = useSubscription()
  const { data: family } = useFamily()
  const planLabel =
    sub?.plan === 'premium'
      ? 'Premium активен'
      : sub?.plan === 'trial'
        ? `Пробный период: ещё ${sub.trial_days_left} дн.`
        : 'Free · прогноз на неделю'

  const items: MenuItem[] = [
    { to: '/premium', icon: Crown, tone: 'bg-amber-50 text-amber-500', title: 'Подписка', hint: planLabel },
    {
      to: '/family',
      icon: Users,
      tone: 'bg-emerald-50 text-emerald-600',
      title: 'Семья',
      hint: family ? `${family.name} · ${family.members.length} участн.` : 'Общий бюджет с близкими',
    },
    {
      to: '/experiments',
      icon: FlaskConical,
      tone: 'bg-brand-50 text-brand-600',
      title: 'Эксперименты',
      hint: 'Стратегии прогноза H0–H3 и бэктест',
    },
  ]

  return (
    <>
      <PageHeader title="Ещё" />
      <Card className="mb-4">
        <p className="font-semibold">{user?.name}</p>
        <p className="text-sm text-slate-500">{user?.email}</p>
      </Card>
      <Card className="mb-4 p-0">
        <ul className="divide-y divide-slate-100">
          {items.map(({ to, icon: Icon, tone, title, hint }) => (
            <li key={to}>
              <Link to={to} className="flex items-center gap-3 p-4">
                <span className={`flex h-10 w-10 items-center justify-center rounded-full ${tone}`}>
                  <Icon className="h-5 w-5" />
                </span>
                <span className="flex-1">
                  <span className="block font-medium">{title}</span>
                  <span className="block text-sm text-slate-500">{hint}</span>
                </span>
                <ChevronRight className="h-5 w-5 text-slate-400" />
              </Link>
            </li>
          ))}
        </ul>
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
