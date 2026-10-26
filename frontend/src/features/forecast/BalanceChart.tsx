import { Area, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { ForecastResult } from '@/api/types'
import { formatDate, formatMoney } from '@/lib/utils'

const LINE = '#2a78d6'
const compact = new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 0 })

export function BalanceChart({ forecast }: { forecast: ForecastResult }) {
  const data = [
    { date: forecast.as_of, expected: forecast.current_balance, band: [forecast.current_balance, forecast.current_balance] },
    ...forecast.daily_balance.map((p) => ({ date: p.date, expected: p.expected, band: [p.p10, p.p90] })),
  ]
  const min = Math.min(0, ...forecast.daily_balance.map((p) => p.p10))
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(d) => formatDate(d, { day: 'numeric', month: 'short' }).replace('.', '')}
            minTickGap={24}
          />
          <YAxis
            width={56}
            tickLine={false}
            axisLine={false}
            domain={[min, 'auto']}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(v) => compact.format(v)}
          />
          <ReferenceLine y={0} stroke="#dc2626" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
            labelFormatter={(d) => formatDate(String(d), { day: 'numeric', month: 'long', weekday: 'short' })}
            formatter={(v, name) =>
              name === 'band'
                ? [`${formatMoney((v as number[])[0])} … ${formatMoney((v as number[])[1])}`, 'Диапазон 80%']
                : [formatMoney(Number(v)), 'Ожидаемый баланс']
            }
          />
          <Area dataKey="band" stroke="none" fill={LINE} fillOpacity={0.15} isAnimationActive={false} />
          <Line dataKey="expected" stroke={LINE} strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
