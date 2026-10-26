import { Area, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { BacktestCase } from '@/api/types'
import { formatDate, formatMoney } from '@/lib/utils'

const FORECAST = '#2a78d6'
const ACTUAL = '#0f172a'
const ORDER = ['forecast', 'actual', 'band']
const compact = new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 0 })

/** Прогноз до конца месяца vs факт для каждой точки отсечения. */
export function CasesChart({ cases }: { cases: BacktestCase[] }) {
  const data = cases.map((c) => ({
    cutoff: c.cutoff,
    forecast: c.forecast,
    actual: c.actual,
    band: [c.p10, c.p90],
  }))
  return (
    <div className="h-60">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="cutoff"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(d) => formatDate(d, { day: 'numeric', month: 'short' }).replace('.', '')}
            minTickGap={16}
          />
          <YAxis
            width={52}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(v) => compact.format(v)}
          />
          <Tooltip
            itemSorter={(item) => ORDER.indexOf(String(item.dataKey))}
            contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
            labelFormatter={(d) => `Прогноз от ${formatDate(String(d))} до конца месяца`}
            formatter={(v, name) =>
              name === 'band'
                ? [`${formatMoney((v as number[])[0])} … ${formatMoney((v as number[])[1])}`, 'Интервал P10–P90']
                : [formatMoney(Number(v)), name === 'forecast' ? 'Прогноз' : 'Факт']
            }
          />
          <Legend
            iconSize={10}
            wrapperStyle={{ fontSize: 12, color: '#475569' }}
            formatter={(v) => ({ forecast: 'Прогноз', actual: 'Факт', band: 'Интервал P10–P90' })[v as string] ?? v}
          />
          <Area dataKey="band" stroke="none" fill={FORECAST} fillOpacity={0.15} isAnimationActive={false} />
          <Line
            dataKey="forecast"
            stroke={FORECAST}
            strokeWidth={2}
            dot={{ r: 3, fill: FORECAST, stroke: '#fff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
          <Line
            dataKey="actual"
            stroke={ACTUAL}
            strokeWidth={0}
            legendType="diamond"
            dot={{ r: 4, fill: ACTUAL, stroke: '#fff', strokeWidth: 2 }}
            activeDot={{ r: 5, fill: ACTUAL }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
