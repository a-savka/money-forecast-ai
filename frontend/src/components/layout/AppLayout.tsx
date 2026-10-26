import { BarChart3, Home, List, Menu, TrendingUp } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { cn } from '@/lib/utils'

const tabs = [
  { to: '/', label: 'Главная', icon: Home, end: true },
  { to: '/transactions', label: 'Операции', icon: List },
  { to: '/forecast', label: 'Прогноз', icon: TrendingUp },
  { to: '/analytics', label: 'Аналитика', icon: BarChart3 },
  { to: '/more', label: 'Ещё', icon: Menu },
]

export function AppLayout() {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col bg-slate-50 shadow-xl">
      <main className="pt-safe flex-1 px-4 pb-24">
        <Outlet />
      </main>
      <nav className="pb-safe fixed bottom-0 left-1/2 z-40 w-full max-w-md -translate-x-1/2 border-t border-slate-200 bg-white/95 backdrop-blur">
        <ul className="grid grid-cols-5">
          {tabs.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    'flex flex-col items-center gap-0.5 py-2 text-[11px]',
                    isActive ? 'text-brand-600' : 'text-slate-500',
                  )
                }
              >
                <Icon className="h-5 w-5" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}

export function PageHeader({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <header className="flex items-center justify-between py-4">
      <h1 className="text-2xl font-bold">{title}</h1>
      {action}
    </header>
  )
}
