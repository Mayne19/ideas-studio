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

const sizes: Record<GaugeSize, { box: string; stroke: number; text: string }> = {
  tiny: { box: 'h-5 w-5', stroke: 10, text: 'text-[0]' },
  small: { box: 'h-12 w-12', stroke: 9, text: 'text-[13px]' },
  medium: { box: 'h-16 w-16', stroke: 9, text: 'text-[18px]' },
  large: { box: 'h-24 w-24', stroke: 8, text: 'text-[30px]' },
}

export function Gauge({
  value,
  size = 'small',
  showValue = false,
  color = '#00c950',
  trackColor = '#e5e5e5',
  className,
}: GaugeProps) {
  const normalized = Math.max(0, Math.min(100, Math.round(value)))
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference * (1 - normalized / 100)
  const config = sizes[size]

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', config.box, className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={normalized}
    >
      <svg className="h-full w-full -rotate-90 overflow-visible" viewBox="0 0 100 100" aria-hidden="true">
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeLinecap="round"
          strokeWidth={config.stroke}
        />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          strokeWidth={config.stroke}
        />
      </svg>
      {showValue && (
        <span className={cn('absolute font-semibold leading-none text-primary tabular-nums', config.text)}>
          {normalized}
        </span>
      )}
    </div>
  )
}
