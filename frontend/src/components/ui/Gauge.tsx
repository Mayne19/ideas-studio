import { cn } from '@/utils/cn'

type GaugeSize = 'tiny' | 'small' | 'medium' | 'large'

type GaugeProps = {
  value: number
  size?: GaugeSize
  showValue?: boolean
  color?: string
  trackColor?: string
  className?: string
}

const sizes: Record<GaugeSize, { box: string; stroke: number; gap: number; text: string }> = {
  tiny: { box: 'h-5 w-5', stroke: 9, gap: 11, text: 'text-[0]' },
  small: { box: 'h-12 w-12', stroke: 8, gap: 14, text: 'text-[14px]' },
  medium: { box: 'h-16 w-16', stroke: 8, gap: 16, text: 'text-[20px]' },
  large: { box: 'h-24 w-24', stroke: 8, gap: 18, text: 'text-[32px]' },
}

export function Gauge({
  value,
  size = 'small',
  showValue = false,
  color = '#45a75a',
  trackColor = '#e8e8e8',
  className,
}: GaugeProps) {
  const normalized = Math.max(0, Math.min(100, Math.round(value)))
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const config = sizes[size]
  const segmentGap = normalized > 0 && normalized < 100 ? config.gap : 0
  const drawableLength = circumference - segmentGap * 2
  const progressLength = drawableLength * (normalized / 100)
  const trackLength = drawableLength - progressLength

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', config.box, className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={normalized}
    >
      <svg className="h-full w-full -rotate-90 overflow-visible" viewBox="0 0 100 100" aria-hidden="true">
        {normalized < 100 && trackLength > 0 && (
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={trackColor}
            strokeDasharray={`${trackLength} ${circumference}`}
            strokeDashoffset={-(segmentGap + progressLength)}
            strokeLinecap="round"
            strokeWidth={config.stroke}
          />
        )}
        {normalized > 0 && (
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={color}
            strokeDasharray={`${progressLength} ${circumference}`}
            strokeLinecap="round"
            strokeWidth={config.stroke}
          />
        )}
      </svg>
      {showValue && (
        <span className={cn('absolute font-semibold leading-none text-[#111111] tabular-nums', config.text)}>
          {normalized}
        </span>
      )}
    </div>
  )
}
