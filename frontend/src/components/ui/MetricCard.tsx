import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type MetricCardTone = 'accent' | 'sky' | 'indigo' | 'violet' | 'orange' | 'success' | 'warning' | 'danger'

type MetricCardProps = {
  icon: ReactNode
  value: ReactNode
  label: string
  suffix?: string
  trend?: string | null
  progress?: number | null
  onClick?: () => void
  tone?: MetricCardTone
  className?: string
}

const toneStyles: Record<MetricCardTone, string> = {
  accent:  'text-accent',
  sky:     'text-accent',
  indigo:  'text-accent',
  violet:  'text-accent',
  orange:  'text-warning',
  success: 'text-success',
  warning: 'text-warning',
  danger:  'text-danger',
}

export default function MetricCard({
  icon, value, label, suffix, trend, progress, onClick, tone = 'accent', className,
}: MetricCardProps) {
  const trendClass = trend?.startsWith('+')
    ? 'bg-success/10 text-success'
    : trend?.startsWith('-')
      ? 'bg-danger/10 text-danger'
      : 'text-tertiary'

  return (
    <div
      className={cn(
        'rounded-[8px] border border-border bg-surface p-4 shadow-card flex flex-col justify-between gap-3',
        onClick && 'cursor-pointer transition-colors hover:border-border-strong hover:bg-bg',
        className,
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[12px] font-medium text-secondary">{label}</p>
        <span className={cn('flex h-5 w-5 shrink-0 items-center justify-center', toneStyles[tone])}>
          {icon}
        </span>
      </div>
      <div>
        <p className="text-[24px] font-semibold text-primary tracking-normal leading-none">
          {value}
          {suffix && <span className="text-[13px] font-normal text-tertiary ml-0.5">{suffix}</span>}
        </p>
        {typeof progress === 'number' && Number.isFinite(progress) && (
          <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface-muted">
            <div
              className={cn(
                'h-full rounded-full',
                progress >= 85 ? 'bg-success' : progress >= 70 ? 'bg-warning' : 'bg-danger',
              )}
              style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }}
            />
          </div>
        )}
      </div>
      <div className="flex min-h-5 items-center justify-between">
        {trend !== undefined && (
          <span className={cn('rounded-full px-1.5 py-0.5 text-[11px] font-medium', trendClass)}>
            {trend ?? '—'}
          </span>
        )}
      </div>
    </div>
  )
}
