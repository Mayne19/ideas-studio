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
  const size = compact ? 'h-5 min-w-7 px-2 text-[12px]' : 'h-5 px-2 text-[12px]'
  return (
    <span className={`inline-flex items-center justify-center rounded-full border font-medium leading-none whitespace-nowrap ${size} ${scoreTone(value, valid)} ${className}`}>
      {showLabel ? `${label} ` : ''}{value === null ? '—' : valid === false ? `${Math.round(value)} incomplet` : Math.round(value)}
    </span>
  )
}
