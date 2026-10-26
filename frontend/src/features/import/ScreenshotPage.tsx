import { ArrowLeft, ImageUp, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Card } from '@/components/ui/card'
import { ErrorMessage, Spinner } from '@/components/ui/feedback'
import { TransactionForm } from '@/features/transactions/TransactionForm'

import { useParseScreenshot } from './api'

export function ScreenshotPage() {
  const navigate = useNavigate()
  const parse = useParseScreenshot()
  const [preview, setPreview] = useState<string | null>(null)

  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview])

  const onFile = (file: File) => {
    setPreview(URL.createObjectURL(file))
    parse.mutate(file)
  }
  const draft = parse.data
  const provider = draft?.info?.llm_provider as string | undefined

  return (
    <div className="mx-auto min-h-full max-w-md space-y-4 bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/transactions" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Скриншот из банка</h1>
      </header>

      {!draft && (
        <Card>
          <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-slate-200 p-6 text-center hover:border-brand-500">
            {parse.isPending ? <Spinner className="h-8 w-8" /> : <ImageUp className="h-8 w-8 text-brand-600" />}
            <span className="font-medium">{parse.isPending ? 'Распознаём…' : 'Выбрать скриншот'}</span>
            <span className="text-sm text-slate-500">
              Экран операции из приложения банка — ИИ найдёт сумму, дату и магазин
            </span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              disabled={parse.isPending}
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) onFile(f)
                e.target.value = ''
              }}
            />
          </label>
        </Card>
      )}

      {preview && (
        <img src={preview} alt="Загруженный скриншот" className="mx-auto max-h-56 rounded-xl border border-slate-200" />
      )}
      {parse.error && <ErrorMessage error={parse.error} />}

      {draft && (
        <Card>
          <p className="mb-1 flex items-center gap-1 text-sm text-slate-500">
            <Sparkles className="h-4 w-4 text-brand-600" /> Проверьте, что распознала модель
            {draft.confidence != null && ` · уверенность ${Math.round(draft.confidence * 100)}%`}
          </p>
          {provider === 'mock' && (
            // MOCK: без ключей vision-LLM результат имитируется; с GigaChat — реальное распознавание
            <p className="mb-3 text-xs text-amber-700">
              Демо-режим: распознавание имитируется. Подключите GigaChat в настройках сервера.
            </p>
          )}
          <TransactionForm draft={draft} onDone={() => navigate('/transactions')} />
        </Card>
      )}
    </div>
  )
}
