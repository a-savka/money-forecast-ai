import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, Server, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, getApiUrl, setApiUrl, unwrap } from '@/api/client'
import type { DemoProfile } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { Input, Label } from '@/components/ui/input'
import { useSession } from '@/store/session'

const PROFILE_EMOJI: Record<string, string> = {
  young: '👨‍💻',
  family: '👨‍👩‍👧',
  freelancer: '🧑‍🎨',
  dropout: '😩',
}

export function LoginPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setSession = useSession((s) => s.setSession)
  const [serverOpen, setServerOpen] = useState(false)
  const [server, setServer] = useState(getApiUrl())

  const profiles = useQuery({
    queryKey: ['demo-profiles', server],
    queryFn: () => unwrap<DemoProfile[]>(api.GET('/auth/demo-profiles')),
  })

  // MOCK: вход без пароля. В реальной версии — email/телефон + код, VK ID, Сбер ID.
  const login = useMutation({
    mutationFn: (profile: string | null) => unwrap(api.POST('/auth/demo-login', { body: { profile } })),
    onSuccess: (data) => {
      qc.clear()
      setSession(data.access_token, data.user)
      navigate(data.user.profile ? '/' : '/onboarding', { replace: true })
    },
  })

  return (
    <div className="pt-safe mx-auto min-h-full max-w-md bg-gradient-to-b from-brand-600 to-brand-700 px-4 pb-8">
      <div className="py-10 text-white">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15 text-3xl">₽</div>
        <h1 className="text-3xl font-bold">MoneyForecast AI</h1>
        <p className="mt-2 text-brand-100">
          Прогноз расходов, который заранее предупреждает о кассовых разрывах
        </p>
      </div>

      <Card className="space-y-3">
        <h2 className="font-semibold">Войти как демо-пользователь</h2>
        {profiles.isLoading && <PageLoader />}
        {profiles.error && <ErrorMessage error={profiles.error} />}
        {profiles.data?.map((p) => (
          <button
            key={p.key}
            disabled={login.isPending}
            onClick={() => login.mutate(p.key)}
            className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left hover:bg-slate-50"
          >
            <span className="text-2xl">{PROFILE_EMOJI[p.key] ?? '🙂'}</span>
            <span className="flex-1">
              <span className="block font-medium">{p.title}</span>
              <span className="block text-sm text-slate-500">{p.description}</span>
            </span>
            <ChevronRight className="h-5 w-5 text-slate-400" />
          </button>
        ))}
        <Button className="w-full" variant="secondary" disabled={login.isPending} onClick={() => login.mutate(null)}>
          <Sparkles className="h-4 w-4" /> Начать с чистого листа
        </Button>
        {login.error && <ErrorMessage error={login.error} />}
      </Card>

      <button
        className="mx-auto mt-6 flex items-center gap-1 text-sm text-brand-100"
        onClick={() => setServerOpen((v) => !v)}
      >
        <Server className="h-4 w-4" /> Настройки сервера
      </button>
      {serverOpen && (
        <Card className="mt-3 space-y-2">
          <Label htmlFor="server">Адрес API</Label>
          <Input id="server" value={server} onChange={(e) => setServer(e.target.value)} placeholder="http://192.168.0.10:8000" />
          <Button
            className="w-full"
            onClick={() => {
              setApiUrl(server)
              setServer(getApiUrl())
            }}
          >
            Сохранить
          </Button>
        </Card>
      )}
    </div>
  )
}
