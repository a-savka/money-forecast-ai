import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Check, CheckCircle2, Landmark, Loader2, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { api, unwrap } from '@/api/client'
import { useInvalidateFinance } from '@/api/hooks'
import type { BankConnectResult, MockBank } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { cn } from '@/lib/utils'

/** Тёмная иконка на светлом фоне банка (жёлтый Т-Банк), светлая — на тёмном. */
function iconColor(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  return 0.299 * r + 0.587 * g + 0.114 * b > 160 ? '#0f172a' : '#ffffff'
}

const STEPS = ['Подключаемся к банку', 'Загружаем операции за 6 месяцев', 'Распознаём категории', 'Готовим первый прогноз']

/**
 * MOCK: подключение банка. В реальной версии — Open Banking / API банка-партнёра
 * с OAuth-согласием на стороне банка. Сейчас операции генерируются на сервере.
 */
export function ConnectBankPage() {
  const navigate = useNavigate()
  // Из онбординга возвращаемся на экран первого прогноза
  const next = useSearchParams()[0].get('next') ?? '/'
  const invalidate = useInvalidateFinance()
  const [bank, setBank] = useState<MockBank | null>(null)
  const [step, setStep] = useState(0)

  const banks = useQuery({
    queryKey: ['mock-banks'],
    queryFn: () => unwrap<MockBank[]>(api.GET('/imports/bank-mock/banks')),
  })
  const connect = useMutation({
    mutationFn: (key: string) =>
      unwrap<BankConnectResult>(api.POST('/imports/bank-mock/connect', { body: { bank: key, months: 6 } })),
    onSuccess: invalidate,
  })

  // Имитация прогресса синхронизации
  useEffect(() => {
    if (!connect.isPending && !connect.isSuccess) return
    if (step >= STEPS.length) return
    const t = setTimeout(() => setStep((s) => s + 1), 700)
    return () => clearTimeout(t)
  }, [connect.isPending, connect.isSuccess, step])

  const finished = connect.isSuccess && step >= STEPS.length

  return (
    <div className="mx-auto min-h-full max-w-md bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/transactions" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Подключить банк</h1>
      </header>

      {!bank && (
        <div className="space-y-3">
          <p className="text-sm text-slate-500">
            Операции будут подтягиваться автоматически — не нужно ничего вводить вручную.
          </p>
          {banks.isLoading && <PageLoader />}
          {banks.error && <ErrorMessage error={banks.error} />}
          <div className="grid grid-cols-2 gap-3">
            {banks.data?.map((b) => (
              <button
                key={b.key}
                onClick={() => setBank(b)}
                className="flex flex-col items-start gap-3 rounded-2xl bg-white p-4 text-left shadow-sm hover:ring-2 hover:ring-brand-500"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl" style={{ backgroundColor: b.color }}>
                  <Landmark className="h-5 w-5" style={{ color: iconColor(b.color) }} />
                </span>
                <span className="font-medium">{b.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {bank && connect.isIdle && (
        <Card className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl" style={{ backgroundColor: bank.color }}>
              <Landmark className="h-6 w-6" style={{ color: iconColor(bank.color) }} />
            </span>
            <div>
              <p className="text-sm text-slate-500">Вход через {bank.name}</p>
              <p className="font-semibold">Запрос доступа</p>
            </div>
          </div>
          <p>
            <b>MoneyForecast AI</b> запрашивает доступ к данным в {bank.name}:
          </p>
          <ul className="space-y-2 text-sm">
            {['Список счетов и карт', 'Баланс', 'История операций за 6 месяцев'].map((x) => (
              <li key={x} className="flex items-center gap-2">
                <Check className="h-4 w-4 text-emerald-600" /> {x}
              </li>
            ))}
          </ul>
          <p className="flex items-start gap-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
            Только чтение. Приложение не может совершать платежи. Доступ можно отозвать в любой момент.
            (Демо-режим: данные сгенерированы.)
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" className="flex-1" onClick={() => setBank(null)}>
              Отмена
            </Button>
            <Button className="flex-1" onClick={() => connect.mutate(bank.key)}>
              Разрешить
            </Button>
          </div>
        </Card>
      )}

      {bank && !connect.isIdle && !finished && (
        <Card className="space-y-3">
          {STEPS.map((s, i) => (
            <div key={s} className={cn('flex items-center gap-3', i > step && 'text-slate-400')}>
              {i < step ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              ) : i === step ? (
                <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
              ) : (
                <span className="h-5 w-5 rounded-full border-2 border-slate-200" />
              )}
              {s}
            </div>
          ))}
          {connect.error && <ErrorMessage error={connect.error} />}
        </Card>
      )}

      {finished && connect.data && (
        <Card className="flex flex-col items-center gap-3 py-8 text-center">
          <CheckCircle2 className="h-12 w-12 text-emerald-500" />
          <h2 className="text-lg font-semibold">{connect.data.account_name} подключена</h2>
          <p className="text-slate-500">Загружено операций: {connect.data.imported}</p>
          <Button className="w-full" onClick={() => navigate(next)}>
            Посмотреть прогноз
          </Button>
        </Card>
      )}
    </div>
  )
}
