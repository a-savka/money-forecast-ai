import { ArrowLeft, Lightbulb, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card } from '@/components/ui/card'
import { EmptyState, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { cn } from '@/lib/utils'
import { useSettings } from '@/store/settings'

import { RecommendationCard } from './RecommendationCard'
import { useRecommendations } from './api'

const MODES = [
  { value: 'rules', label: 'Правила' },
  { value: 'llm', label: 'ИИ-формулировки' },
] as const

export function RecommendationsPage() {
  const { data, isLoading, error } = useRecommendations()
  const mode = useSettings((s) => s.recommendationsMode)
  const setMode = useSettings((s) => s.setRecommendationsMode)
  const provider = data?.info?.llm_provider as string | undefined

  return (
    <div className="mx-auto min-h-full max-w-md bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Советы</h1>
      </header>

      <div className="mb-4 grid grid-cols-2 gap-1 rounded-xl bg-slate-200 p-1" role="tablist">
        {MODES.map((m) => (
          <button
            key={m.value}
            role="tab"
            aria-selected={mode === m.value}
            onClick={() => setMode(m.value)}
            className={cn(
              'rounded-lg py-1.5 text-sm font-medium',
              mode === m.value ? 'bg-white shadow-sm' : 'text-slate-600',
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {isLoading && <PageLoader />}
      {error && <ErrorMessage error={error} />}
      {data && data.items.length === 0 && (
        <EmptyState icon={<Lightbulb className="h-8 w-8" />} title="Пока советов нет">
          {data.info?.reason === 'no_data'
            ? 'Советы появятся, когда в приложении будут операции.'
            : 'Финансы выглядят стабильно — заглядывайте после новых операций.'}
        </EmptyState>
      )}
      {data && data.items.length > 0 && (
        <Card>
          <ul className="divide-y divide-slate-100">
            {data.items.map((r) => (
              <RecommendationCard key={r.id} rec={r} />
            ))}
          </ul>
        </Card>
      )}
      {data?.mode === 'llm' && (
        <p className="mt-3 flex items-center gap-1 text-xs text-slate-500">
          <Sparkles className="h-3 w-3" />
          Тексты переписаны LLM ({provider ?? 'mock'}); суммы считаются правилами и не меняются.
        </p>
      )}
    </div>
  )
}
