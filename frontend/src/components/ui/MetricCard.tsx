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
  accent:  'bg-accent/10 text-accent',
  sky:     'bg-accent/10 text-accent',
  indigo:  'bg-brand-soft text-accent',
  violet:  'bg-brand-soft text-accent',
  orange:  'bg-warning/10 text-warning',
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  danger:  'bg-danger/10 text-danger',
}

export default function MetricCard({
  icon, value, label, suffix, trend, onClick, tone = 'accent', className,
}: MetricCardProps) {
  const trendClass = trend?.startsWith('+')
    ? 'bg-success/10 text-success'
    : trend?.startsWith('-')
      ? 'bg-danger/10 text-danger'
      : 'text-tertiary'

  return (
    <div
      className={cn(
        'rounded-[8px] bg-surface p-4 flex flex-col justify-between gap-2',
        onClick && 'cursor-pointer transition-colors hover:bg-surface-soft',
        className,
      )}
      onClick={onClick}
    >
      <span className={cn('flex h-8 w-8 items-center justify-center rounded-[6px]', toneStyles[tone])}>
        {icon}
      </span>
      <p className="text-[24px] font-semibold text-primary tracking-tight leading-none">
        {value}
        {suffix && <span className="text-[14px] font-normal text-tertiary ml-0.5">{suffix}</span>}
      </p>
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-tertiary">{label}</p>
        {trend !== undefined && (
          <span className={cn('rounded-full px-1.5 py-0.5 text-[11px] font-medium', trendClass)}>
            {trend ?? '—'}
          </span>
        )}
      </div>
    </div>
  )
}
