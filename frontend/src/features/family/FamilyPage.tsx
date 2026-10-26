import { ArrowLeft, Copy, Crown, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import type { FamilyInfo } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Badge, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { Input, Label } from '@/components/ui/input'
import { useIsPremium } from '@/features/subscription/api'
import { formatMoney } from '@/lib/utils'

import { useAddDemoMember, useCreateFamily, useFamily, useJoinFamily, useLeaveFamily } from './api'

export function FamilyPage() {
  const { data: family, isLoading, error } = useFamily()
  return (
    <div className="mx-auto min-h-full max-w-md space-y-4 bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/more" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Семейный бюджет</h1>
      </header>
      {isLoading && <PageLoader />}
      {error && <ErrorMessage error={error} />}
      {family === null && <NoFamily />}
      {family && <FamilyView family={family} />}
    </div>
  )
}

function NoFamily() {
  const isPremium = useIsPremium()
  const create = useCreateFamily()
  const join = useJoinFamily()
  const [name, setName] = useState('Моя семья')
  const [code, setCode] = useState('')

  return (
    <>
      <Card className="space-y-2">
        <Users className="h-8 w-8 text-brand-600" />
        <p className="font-semibold">Ведите бюджет вместе</p>
        <p className="text-sm text-slate-600">
          Общий баланс и траты всех участников в одном месте — видно, хватит ли семье денег до зарплаты.
        </p>
      </Card>

      <Card className="space-y-3">
        <CardTitle>Создать семью</CardTitle>
        {isPremium ? (
          <>
            <div className="space-y-1">
              <Label htmlFor="family-name">Название</Label>
              <Input id="family-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={64} />
            </div>
            <Button className="w-full" onClick={() => create.mutate(name)} disabled={create.isPending}>
              Создать
            </Button>
            {create.error && <ErrorMessage error={create.error} />}
          </>
        ) : (
          <Link to="/premium" className="flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-sm">
            <Crown className="h-5 w-5 shrink-0 text-amber-500" />
            Создание семьи доступно в Premium — попробуйте 7 дней бесплатно
          </Link>
        )}
      </Card>

      <Card className="space-y-3">
        <CardTitle>Присоединиться по коду</CardTitle>
        <div className="flex gap-2">
          <Input
            aria-label="Код приглашения"
            placeholder="Например, K7M2QX"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            className="font-mono tracking-widest"
            maxLength={12}
          />
          <Button onClick={() => join.mutate(code)} disabled={code.length < 4 || join.isPending}>
            Войти
          </Button>
        </div>
        {join.error && <ErrorMessage error={join.error} />}
      </Card>
    </>
  )
}

function FamilyView({ family }: { family: FamilyInfo }) {
  const addDemo = useAddDemoMember()
  const leave = useLeaveFamily()
  const [copied, setCopied] = useState(false)
  const isOwner = family.my_role === 'owner'

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(family.invite_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // буфер обмена недоступен (например, без HTTPS) — код и так виден на экране
    }
  }

  return (
    <>
      <Card className="space-y-1 bg-gradient-to-br from-brand-600 to-brand-700 text-white">
        <p className="text-brand-100">{family.name}</p>
        <p className="text-3xl font-bold tabular-nums">{formatMoney(family.total_balance)}</p>
        <p className="text-sm text-brand-100">
          общий баланс · потрачено в этом месяце {formatMoney(family.total_month_expense)}
        </p>
      </Card>

      <Card>
        <CardTitle className="mb-2">Участники</CardTitle>
        <ul className="divide-y divide-slate-100">
          {family.members.map((m) => {
            const share = family.total_month_expense ? m.month_expense / family.total_month_expense : 0
            return (
              <li key={m.user_id} className="py-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 font-semibold text-brand-700">
                    {m.name.slice(0, 1)}
                  </span>
                  <span className="flex-1">
                    <span className="font-medium">
                      {m.name}
                      {m.is_me && <span className="text-slate-400"> (вы)</span>}
                    </span>
                    {m.role === 'owner' && (
                      <Badge tone="brand" className="ml-1">
                        владелец
                      </Badge>
                    )}
                  </span>
                  <span className="font-semibold tabular-nums">{formatMoney(m.balance)}</span>
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-[#2a78d6]" style={{ width: `${Math.round(share * 100)}%` }} />
                  </div>
                  <span className="w-40 text-right tabular-nums">
                    траты {formatMoney(m.month_expense)} · {Math.round(share * 100)}%
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
      </Card>

      {isOwner && (
        <Card className="space-y-3">
          <CardTitle>Пригласить</CardTitle>
          <div className="flex items-center gap-2">
            <span className="flex-1 rounded-xl bg-slate-100 py-2 text-center font-mono text-xl tracking-[0.3em]">
              {family.invite_code}
            </span>
            <Button variant="secondary" size="icon" onClick={copy} aria-label="Скопировать код">
              <Copy className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-slate-500">
            {copied ? 'Код скопирован' : 'Отправьте код близким: «Ещё → Семья → Присоединиться по коду».'}
          </p>
          <Button variant="secondary" className="w-full" onClick={() => addDemo.mutate(undefined)} disabled={addDemo.isPending}>
            <UserPlus className="h-4 w-4" /> Добавить демо-участника
          </Button>
          {addDemo.error && <ErrorMessage error={addDemo.error} />}
        </Card>
      )}

      <Button variant="ghost" className="w-full text-red-600" onClick={() => leave.mutate(undefined)} disabled={leave.isPending}>
        {isOwner ? 'Распустить семью' : 'Выйти из семьи'}
      </Button>
    </>
  )
}
