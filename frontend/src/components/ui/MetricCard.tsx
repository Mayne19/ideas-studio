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
  sky:     'bg-sky-500/10 text-sky-600',
  indigo:  'bg-indigo-500/10 text-indigo-600',
  violet:  'bg-violet-500/10 text-violet-600',
  orange:  'bg-orange-500/10 text-orange-600',
  success: 'bg-success/10 text-[#1a7a3a]',
  warning: 'bg-warning/12 text-[#b46a00]',
  danger:  'bg-danger/10 text-danger',
}

export default function MetricCard({
  icon, value, label, suffix, trend, onClick, tone = 'accent', className,
}: MetricCardProps) {
  const trendClass = trend?.startsWith('+')
    ? 'bg-success/10 text-[#1a7a3a]'
    : trend?.startsWith('-')
      ? 'bg-danger/10 text-danger'
      : 'text-tertiary'

  return (
    <div
      className={cn(
        'rounded-[22px] bg-surface p-4 flex flex-col justify-between gap-2',
        onClick && 'cursor-pointer transition-colors hover:bg-white',
        className,
      )}
      onClick={onClick}
    >
      <span className={cn('flex h-8 w-8 items-center justify-center rounded-[10px]', toneStyles[tone])}>
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
