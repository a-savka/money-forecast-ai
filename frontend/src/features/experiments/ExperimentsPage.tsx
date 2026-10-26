import { ArrowLeft, Check, FlaskConical, Play, Trophy } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { BacktestRun } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Badge, EmptyState, ErrorMessage, PageLoader } from '@/components/ui/feedback'
import { Select } from '@/components/ui/input'
import { useStrategies } from '@/features/forecast/api'
import { cn, formatDate, formatMoney } from '@/lib/utils'
import { useSettings } from '@/store/settings'

import { CasesChart } from './CasesChart'
import { latestBatch, useExperiments, useRunBacktest } from './api'

const DATASET_TITLES: Record<string, string> = {
  young: 'Молодой специалист',
  family: 'Семья',
  freelancer: 'Фрилансер',
  dropout: '«Бросивший» учёт',
  me: 'Мои данные',
}

const pct = (v: unknown) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—')

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
}) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-200 p-1" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'flex-1 whitespace-nowrap rounded-lg px-2 py-1.5 text-sm font-medium',
            value === o.value ? 'bg-white shadow-sm' : 'text-slate-600',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function ExperimentsPage() {
  const { data: strategies = [] } = useStrategies()
  const active = useSettings((s) => s.strategy)
  const setActive = useSettings((s) => s.setStrategy)
  const titles = Object.fromEntries(strategies.map((s) => [s.name, s.title]))

  const experiments = useExperiments()
  const run = useRunBacktest()
  const [dataset, setDataset] = useState<'demo' | 'me'>('demo')
  const [months, setMonths] = useState(3)

  const batch = useMemo(() => latestBatch(experiments.data ?? []), [experiments.data])
  const ranked = [...batch].sort((a, b) => Number(a.metrics.wape) - Number(b.metrics.wape))

  return (
    <div className="mx-auto min-h-full max-w-md space-y-4 bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/more" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Эксперименты</h1>
      </header>

      <Card>
        <CardTitle className="mb-2">Стратегия прогноза</CardTitle>
        <ul className="space-y-2" role="radiogroup">
          {strategies.map((s) => (
            <li key={s.name}>
              <button
                role="radio"
                aria-checked={active === s.name}
                onClick={() => setActive(s.name)}
                className={cn(
                  'flex w-full items-start gap-3 rounded-xl border p-3 text-left',
                  active === s.name ? 'border-brand-500 bg-brand-50' : 'border-slate-200',
                )}
              >
                <span
                  className={cn(
                    'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                    active === s.name ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300',
                  )}
                >
                  {active === s.name && <Check className="h-3 w-3" />}
                </span>
                <span>
                  <span className="block font-medium">{s.title}</span>
                  <span className="block text-sm text-slate-500">{s.description}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-500">Выбранная стратегия используется на главной, в прогнозе и советах.</p>
      </Card>

      <Card className="space-y-3">
        <CardTitle className="flex items-center gap-1">
          <FlaskConical className="h-4 w-4" /> Сравнение на истории (бэктест)
        </CardTitle>
        <p className="text-sm text-slate-600">
          Модель «откатывается» в прошлое — на 1, 10 и 20 число месяца — и прогнозирует траты до конца
          месяца. Прогноз сравнивается с тем, что было на самом деле.
        </p>
        <Segmented
          value={dataset}
          onChange={setDataset}
          options={[
            { value: 'demo', label: '4 демо-профиля' },
            { value: 'me', label: 'Мои данные' },
          ]}
        />
        <div className="flex items-center gap-2">
          <Select
            aria-label="Период"
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
            className="w-auto flex-1"
          >
            <option value={3}>3 месяца</option>
            <option value={6}>6 месяцев</option>
          </Select>
          <Button onClick={() => run.mutate({ dataset, months, strategies: null })} disabled={run.isPending}>
            <Play className="h-4 w-4" /> {run.isPending ? 'Считаем…' : 'Запустить'}
          </Button>
        </div>
        {run.isPending && <p className="text-xs text-slate-500">Это займёт 5–15 секунд.</p>}
        {run.error && <ErrorMessage error={run.error} />}
      </Card>

      {experiments.isLoading && <PageLoader />}
      {experiments.data && batch.length === 0 && !run.isPending && (
        <EmptyState icon={<FlaskConical className="h-8 w-8" />} title="Бэктест ещё не запускался">
          Нажмите «Запустить», чтобы сравнить стратегии H0–H3.
        </EmptyState>
      )}
      {ranked.length > 0 && <Results runs={ranked} titles={titles} />}
    </div>
  )
}

function Results({ runs, titles }: { runs: BacktestRun[]; titles: Record<string, string> }) {
  const [strategy, setStrategy] = useState(runs[0].strategy)
  const current = runs.find((r) => r.strategy === strategy) ?? runs[0]
  const datasets = [...new Set(current.cases.map((c) => c.dataset))]
  const [dataset, setDataset] = useState(datasets[0])
  const ds = datasets.includes(dataset) ? dataset : datasets[0]
  const meta = runs[0]

  return (
    <>
      <Card>
        <CardTitle className="mb-1">Результаты</CardTitle>
        <p className="mb-2 text-xs text-slate-500">
          {formatDate(meta.created_at.slice(0, 10))} · {String(meta.metrics.cases)} прогнозов на стратегию ·{' '}
          {(meta.params.datasets as string[] | undefined)?.map((d) => DATASET_TITLES[d] ?? d).join(', ')}
        </p>
        <div className="-mx-4 overflow-x-auto px-4">
          <table className="w-full min-w-[480px] text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-1 font-medium">Стратегия</th>
                <th className="py-1 pl-3 text-right font-medium">WAPE</th>
                <th className="py-1 pl-3 text-right font-medium">MAE</th>
                <th className="py-1 pl-3 text-right font-medium">P10–P90</th>
                <th className="py-1 pl-3 text-right font-medium">Разрыв, recall</th>
                <th className="py-1 pl-3 text-right font-medium">мс</th>
                <th className="py-1 pl-3 text-right font-medium">LLM</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 tabular-nums">
              {runs.map((r, i) => (
                <tr key={r.id}>
                  <td className="py-2 pr-2">
                    <span className="font-medium">{titles[r.strategy] ?? r.strategy}</span>
                    {i === 0 && (
                      <Badge tone="green" className="ml-1">
                        <Trophy className="h-3 w-3" /> лучшая
                      </Badge>
                    )}
                  </td>
                  <td className="py-2 pl-3 text-right font-semibold">{pct(r.metrics.wape)}</td>
                  <td className="py-2 pl-3 text-right">{formatMoney(Number(r.metrics.mae))}</td>
                  <td className="py-2 pl-3 text-right">{pct(r.metrics.coverage_p10_p90)}</td>
                  <td className="py-2 pl-3 text-right">{pct(r.metrics.gap_recall)}</td>
                  <td className="py-2 pl-3 text-right">{String(r.metrics.latency_ms)}</td>
                  <td className="py-2 pl-3 text-right">{r.llm_cost ? `${r.llm_cost.toFixed(2)} ₽` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <dl className="mt-3 space-y-1 text-xs text-slate-500">
          <div>
            <dt className="inline font-medium text-slate-600">WAPE</dt> — суммарная ошибка / суммарные траты, меньше —
            лучше.
          </div>
          <div>
            <dt className="inline font-medium text-slate-600">P10–P90</dt> — как часто факт попал в интервал прогноза
            (в идеале ≈ 80%).
          </div>
          <div>
            <dt className="inline font-medium text-slate-600">Разрыв, recall</dt> — доля реальных уходов в минус, о
            которых модель предупредила.
          </div>
        </dl>
      </Card>

      <Card className="space-y-3">
        <CardTitle>Прогноз и факт</CardTitle>
        <Select aria-label="Стратегия" value={current.strategy} onChange={(e) => setStrategy(e.target.value)}>
          {runs.map((r) => (
            <option key={r.strategy} value={r.strategy}>
              {titles[r.strategy] ?? r.strategy}
            </option>
          ))}
        </Select>
        {datasets.length > 1 && (
          <Select aria-label="Профиль" value={ds} onChange={(e) => setDataset(e.target.value)}>
            {datasets.map((d) => (
              <option key={d} value={d}>
                {DATASET_TITLES[d] ?? d}
              </option>
            ))}
          </Select>
        )}
        <CasesChart cases={current.cases.filter((c) => c.dataset === ds)} />
      </Card>
    </>
  )
}
