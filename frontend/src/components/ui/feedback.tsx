import { Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-6 w-6 animate-spin text-brand-600', className)} />
}

export function PageLoader() {
  return (
    <div className="flex h-40 items-center justify-center">
      <Spinner />
    </div>
  )
}

export function EmptyState({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center text-slate-500">
      {icon}
      <p className="font-medium text-slate-700">{title}</p>
      {children}
    </div>
  )
}

export function ErrorMessage({ error }: { error: unknown }) {
  const text = error instanceof Error ? error.message : 'Что-то пошло не так'
  return <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{text}</div>
}

const badgeTones = {
  slate: 'bg-slate-100 text-slate-700',
  green: 'bg-emerald-100 text-emerald-700',
  amber: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-700',
  brand: 'bg-brand-100 text-brand-700',
}

export function Badge({
  tone = 'slate',
  className,
  children,
}: {
  tone?: keyof typeof badgeTones
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', badgeTones[tone], className)}
    >
      {children}
    </span>
  )
}
