import { cn } from '@/utils/cn'

type SeoScoreIndicatorProps = {
  value: number | null | undefined
  compact?: boolean
  className?: string
}

function normalizeScore(value: number | null | undefined): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return Math.max(0, Math.min(value, 100))
}

function scoreColor(score: number | null): string {
  if (score === null) return 'bg-border-strong'
  if (score >= 85) return 'bg-success'
  if (score >= 70) return 'bg-warning'
  return 'bg-danger'
}

export default function SeoScoreIndicator({ value, compact = false, className }: SeoScoreIndicatorProps) {
  const score = normalizeScore(value)

  return (
    <div className={cn('min-w-[88px]', className)}>
      <div className="mb-1 flex items-baseline justify-between gap-2">
        {!compact && <span className="text-[11px] font-medium text-tertiary">Score SEO</span>}
        <span className="text-[12px] font-semibold tabular-nums text-primary">
          {score === null ? '—' : Math.round(score)}
        </span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-muted">
        <div
          className={cn('h-full rounded-full transition-all', scoreColor(score))}
          style={{ width: `${score ?? 0}%` }}
        />
      </div>
    </div>
  )
}
