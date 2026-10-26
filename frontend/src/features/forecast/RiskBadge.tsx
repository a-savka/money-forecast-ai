import { AlertTriangle, CheckCircle2, OctagonAlert } from 'lucide-react'

import { cn } from '@/lib/utils'

const RISK = {
  low: { label: 'низкий', icon: CheckCircle2, className: 'bg-emerald-50 text-emerald-700' },
  medium: { label: 'средний', icon: AlertTriangle, className: 'bg-amber-50 text-amber-800' },
  high: { label: 'высокий', icon: OctagonAlert, className: 'bg-red-50 text-red-700' },
} as const

export type RiskLevel = keyof typeof RISK

/** Статус всегда с иконкой и словом — не только цветом. */
export function RiskBadge({ risk, className }: { risk: string; className?: string }) {
  const r = RISK[(risk as RiskLevel) in RISK ? (risk as RiskLevel) : 'low']
  const Icon = r.icon
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium', r.className, className)}>
      <Icon className="h-4 w-4" />
      Риск уйти в минус — {r.label}
    </span>
  )
}
