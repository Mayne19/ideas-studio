import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type MetricCardTone = 'accent' | 'sky' | 'indigo' | 'violet' | 'orange' | 'success' | 'warning' | 'danger'

type MetricCardProps = {
  icon: ReactNode
  value: ReactNode
  label: string
  suffix?: string
  trend?: string | null
  onClick?: () => void
  tone?: MetricCardTone
  className?: string
}

const toneStyles: Record<MetricCardTone, string> = {
  accent:  'bg-surface-soft text-primary',
  sky:     'bg-blue-50 text-blue-700',
  indigo:  'bg-indigo-50 text-indigo-700',
  violet:  'bg-violet-50 text-violet-700',
  orange:  'bg-orange-50 text-orange-700',
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-700',
  danger:  'bg-red-50 text-red-700',
}

export default function MetricCard({
  icon, value, label, suffix, trend, onClick, tone = 'accent', className,
}: MetricCardProps) {
  const trendClass = trend?.startsWith('+')
    ? 'border-green-200 bg-green-50 text-green-700'
    : trend?.startsWith('-')
      ? 'border-red-200 bg-red-50 text-red-700'
      : 'border-border bg-surface-soft text-tertiary'

  return (
    <div
      className={cn(
        'rounded-[8px] border-2 border-border bg-transparent p-4 flex flex-col justify-between gap-2 shadow-none',
        onClick && 'cursor-pointer transition-colors hover:bg-surface-soft',
        className,
      )}
      onClick={onClick}
    >
      <span className={cn('flex h-8 w-8 items-center justify-center rounded-[8px]', toneStyles[tone])}>
        {icon}
      </span>
      <p className="text-[24px] font-semibold text-primary tracking-tight leading-none">
        {value}
        {suffix && <span className="text-[14px] font-normal text-tertiary ml-0.5">{suffix}</span>}
      </p>
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-tertiary">{label}</p>
        {trend !== undefined && (
          <span className={cn('rounded-full border px-1.5 py-0.5 text-[11px] font-medium', trendClass)}>
            {trend ?? '—'}
          </span>
        )}
      </div>
    </div>
  )
}
