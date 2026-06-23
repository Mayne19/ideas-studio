import { scoreTone } from '@/lib/scoreBadge'

interface ScoreBadgeProps {
  label: string
  value: number | null
  showLabel?: boolean
  valid?: boolean | null
  compact?: boolean
  className?: string
}

export default function ScoreBadge({ label, value, showLabel = true, valid, compact = false, className = '' }: ScoreBadgeProps) {
  const size = compact ? 'text-[8px] px-1 py-0.5' : 'text-[10px] px-1.5 py-0.5'
  return (
    <span className={`inline-flex items-center rounded-full font-medium whitespace-nowrap ${size} ${scoreTone(value, valid)} ${className}`}>
      {showLabel ? `${label} ` : ''}{value === null ? '—' : valid === false ? `${Math.round(value)} incomplet` : Math.round(value)}
    </span>
  )
}
