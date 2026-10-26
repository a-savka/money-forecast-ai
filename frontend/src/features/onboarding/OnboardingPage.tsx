import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronRight,
  FileSpreadsheet,
  Landmark,
  PencilLine,
  PiggyBank,
  ShieldAlert,
  Sparkles,
  Target,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, unwrap } from '@/api/client'
import { ErrorMessage } from '@/components/ui/feedback'
import { cn } from '@/lib/utils'
import { markOnboardingStart, onboardingElapsed, track } from '@/lib/track'
import { useSettings } from '@/store/settings'

const AHA = '/onboarding/aha'

const GOALS: { value: string; icon: LucideIcon; title: string; hint: string }[] = [
  { value: 'no_gap', icon: ShieldAlert, title: 'Не уходить в минус', hint: 'Знать заранее, хватит ли до зарплаты' },
  { value: 'control', icon: Target, title: 'Контролировать траты', hint: 'Понять, куда уходят деньги' },
  { value: 'save', icon: PiggyBank, title: 'Начать копить', hint: 'Найти, что можно отложить' },
]

function Option({ icon: Icon, title, hint, onClick, accent, disabled }: {
  icon: LucideIcon
  title: string
  hint: string
  onClick: () => void
  accent?: boolean
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex w-full items-center gap-3 rounded-2xl border bg-white p-4 text-left shadow-sm transition hover:border-brand-500 disabled:opacity-60',
        accent ? 'border-brand-500 ring-2 ring-brand-100' : 'border-slate-200',
      )}
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
        <Icon className="h-5 w-5" />
      </span>
      <span className="flex-1">
        <span className="block font-semibold">{title}</span>
        <span className="block text-sm text-slate-500">{hint}</span>
      </span>
      <ChevronRight className="h-5 w-5 text-slate-400" />
    </button>
  )
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setGoal = useSettings((s) => s.setGoal)
  const [step, setStep] = useState<1 | 2>(1)

  useEffect(() => {
    if (onboardingElapsed() === null) {
      markOnboardingStart()
      track('onboarding_started')
    }
  }, [])

  // Демо-данные: загружаем профиль «бросившего учёт» — у него виден риск разрыва
  const demo = useMutation({
    mutationFn: () => unwrap(api.POST('/dev/seed', { body: { profile: 'dropout', months: 12, seed: 42 } })),
    onSuccess: async () => {
      await qc.invalidateQueries()
      navigate(`${AHA}?source=demo`)
    },
  })

  return (
    <div className="pt-safe mx-auto min-h-full max-w-md bg-slate-50 px-4 pb-10">
      <div className="flex gap-1 py-4" aria-label={`Шаг ${step} из 3`}>
        {[1, 2, 3].map((i) => (
          <span key={i} className={cn('h-1.5 flex-1 rounded-full', i <= step ? 'bg-brand-600' : 'bg-slate-200')} />
        ))}
      </div>

      {step === 1 && (
        <div className="space-y-3">
          <h1 className="text-2xl font-bold">Что для вас главное?</h1>
          <p className="text-slate-600">Под эту цель настроим прогноз и советы.</p>
          {GOALS.map((g) => (
            <Option
              key={g.value}
              {...g}
              onClick={() => {
                setGoal(g.value)
                setStep(2)
              }}
            />
          ))}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <h1 className="text-2xl font-bold">Откуда взять операции?</h1>
          <p className="text-slate-600">Через минуту покажем прогноз трат до конца месяца.</p>
          <Option
            icon={Landmark}
            title="Подключить банк"
            hint="Т-Банк, Сбер, Альфа… — 10 секунд"
            accent
            onClick={() => navigate(`/connect-bank?next=${encodeURIComponent(`${AHA}?source=bank`)}`)}
          />
          <Option
            icon={FileSpreadsheet}
            title="Загрузить выписку"
            hint="CSV или Excel из приложения банка"
            onClick={() => navigate(`/import?next=${encodeURIComponent(`${AHA}?source=statement`)}`)}
          />
          <Option
            icon={Sparkles}
            title="Посмотреть на демо-данных"
            hint="12 месяцев операций типичного пользователя"
            disabled={demo.isPending}
            onClick={() => demo.mutate()}
          />
          <Option
            icon={PencilLine}
            title="Ввести вручную"
            hint="Прогноз появится, когда наберётся история"
            onClick={() => navigate('/transactions')}
          />
          {demo.error && <ErrorMessage error={demo.error} />}
          <button className="w-full py-2 text-sm text-slate-500" onClick={() => setStep(1)}>
            Назад
          </button>
        </div>
      )}
    </div>
  )
}
