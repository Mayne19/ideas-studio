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
  sky:     'bg-accent/8 text-accent',
  indigo:  'bg-accent/8 text-accent',
  violet:  'bg-accent/8 text-accent',
  orange:  'bg-warning/8 text-warning',
  success: 'bg-success/8 text-success',
  warning: 'bg-warning/8 text-warning',
  danger:  'bg-danger/8 text-danger',
}

export default function MetricCard({
  icon, value, label, suffix, trend, onClick, tone = 'accent', className,
}: MetricCardProps) {
  const trendClass = trend?.startsWith('+')
    ? 'border-success/20 bg-success/8 text-success'
    : trend?.startsWith('-')
      ? 'border-danger/20 bg-danger/8 text-danger'
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
        {suffix && <span className="text-[15px] font-normal text-tertiary ml-0.5">{suffix}</span>}
      </p>
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-tertiary">{label}</p>
        {trend !== undefined && (
          <span className={cn('rounded-full border px-1.5 py-0.5 text-[12px] font-medium', trendClass)}>
            {trend ?? '—'}
          </span>
        )}
      </div>
    </div>
  )
}
