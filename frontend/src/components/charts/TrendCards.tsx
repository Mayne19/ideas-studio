import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { HelpCircle } from '@/components/ui/hugeIcons'
import { Gauge } from '@vercel/geistcn/components'

export type MonthPoint = { v: number }

export function SeoRadialCard({
  title,
  score,
  changePts,
  data,
  color,
}: {
  title: string
  score: number
  changePts: number
  data: MonthPoint[]
  color?: string
}) {
  const fillColor = color ?? (score >= 75 ? '#45a75a' : score >= 50 ? '#ffa51f' : '#ff3b1f')
  const changeColor = fillColor
  const changeLabel = changePts >= 0 ? `+${changePts} pts` : `${changePts} pts`

  return (
    <article className="flex h-[148px] flex-col rounded-[10px] border-2 border-border bg-transparent px-5 py-4 shadow-none">
      <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-medium leading-none text-tertiary">
        <span className="truncate whitespace-nowrap">{title}</span>
        <HelpCircle size={12} className="shrink-0 text-tertiary" />
      </div>
      <div className="mt-3 flex h-8 items-center justify-between gap-3">
        <Gauge showValue size="small" value={score} color={fillColor} />
        <span className="text-[12px] font-semibold leading-none tabular-nums" style={{ color: changeColor }}>{changeLabel}</span>
      </div>
      <div className="mt-2 h-[60px] -mx-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 6, bottom: 6, left: 6 }}>
            <Area
              type="natural"
              dataKey="v"
              stroke={fillColor}
              strokeWidth={1.5}
              fill={fillColor}
              fillOpacity={0.22}
              dot={{ r: 1.5, fill: fillColor, strokeWidth: 0 }}
              activeDot={{ r: 2.5, fill: fillColor, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}

export function AreaMetricCard({
  title,
  value,
  change,
  changeColor,
  color,
  data,
}: {
  title: string
  value: string | number
  change: string
  changeColor: string
  color: string
  data: MonthPoint[]
}) {
  return (
    <article className="flex h-[148px] flex-col rounded-[10px] border-2 border-border bg-transparent px-5 py-4 shadow-none">
      <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-medium leading-none text-tertiary">
        <span className="truncate whitespace-nowrap">{title}</span>
        <HelpCircle size={12} className="shrink-0 text-tertiary" />
      </div>
      <div className="mt-3 flex h-8 items-center justify-between gap-3">
        <div className="text-[22px] font-semibold leading-none text-primary">{value}</div>
        <span className="text-[12px] font-semibold leading-none tabular-nums" style={{ color: changeColor }}>{change}</span>
      </div>
      <div className="mt-2 h-[60px] -mx-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 6, bottom: 6, left: 6 }}>
            <Area
              type="linear"
              dataKey="v"
              stroke={color}
              strokeWidth={1.5}
              fill={color}
              fillOpacity={0.08}
              dot={{ r: 1.5, fill: color, strokeWidth: 0 }}
              activeDot={{ r: 2.5, fill: color, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}
