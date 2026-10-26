import { AlertTriangle, Bell, OctagonAlert, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { cn } from '@/lib/utils'
import { useToasts } from '@/store/toast'

const SEVERITY = {
  info: { icon: Bell, tone: 'text-brand-600', label: 'Информация' },
  warning: { icon: AlertTriangle, tone: 'text-amber-600', label: 'Внимание' },
  critical: { icon: OctagonAlert, tone: 'text-red-600', label: 'Важно' },
} as const

/** Веб-замена системных уведомлений: карточки сверху экрана. */
export function Toaster() {
  const { toasts, dismiss } = useToasts()
  const navigate = useNavigate()
  if (!toasts.length) return null
  return (
    <div className="pt-safe pointer-events-none fixed inset-x-0 top-0 z-50 mx-auto max-w-md space-y-2 p-3" aria-live="polite">
      {toasts.map((t) => {
        const s = SEVERITY[t.severity]
        const Icon = s.icon
        return (
          <div
            key={t.id}
            role="status"
            className="pointer-events-auto flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-lg"
          >
            <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', s.tone)} aria-label={s.label} />
            <button
              className="min-w-0 flex-1 text-left"
              onClick={() => {
                dismiss(t.id)
                navigate(t.link)
              }}
            >
              <span className="block text-sm font-semibold">{t.title}</span>
              <span className="block text-sm text-slate-600">{t.body}</span>
            </button>
            <button onClick={() => dismiss(t.id)} className="rounded-full p-1 text-slate-400 hover:bg-slate-100" aria-label="Закрыть">
              <X className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
