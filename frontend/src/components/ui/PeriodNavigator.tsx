import { ArrowLeft, ArrowRight } from 'lucide-react'
import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'
import { currentPeriod, isFuturePeriod, shiftPeriod, type PeriodMode, type PeriodRange } from '@/utils/periodNavigator'

const MODES: Array<{ value: PeriodMode; label: string }> = [
  { value: 'day', label: 'Aujourd’hui' },
  { value: 'week', label: 'Cette semaine' },
  { value: 'month', label: 'Ce mois-ci' },
  { value: 'year', label: 'Cette année' },
]

type PeriodNavigatorProps = {
  value: PeriodRange
  onChange: (range: PeriodRange) => void
  className?: string
}

export default function PeriodNavigator({ value, onChange, className }: PeriodNavigatorProps) {
  const nextRange = shiftPeriod(value, 1)
  const disableNext = isFuturePeriod(nextRange)

  return (
    <div className={cn('flex flex-wrap items-center justify-end gap-2', className)}>
      <div className="flex items-center rounded-[12px] bg-surface-soft p-1">
        <button
          type="button"
          onClick={() => onChange(shiftPeriod(value, -1))}
          className="flex h-8 w-8 items-center justify-center rounded-[9px] text-secondary transition-colors hover:bg-surface hover:text-primary"
          aria-label="Période précédente"
        >
          <ArrowLeft size={14} />
        </button>
        <span className="min-w-[220px] px-3 text-center text-[12px] font-medium text-secondary">
          {value.label}
        </span>
        <button
          type="button"
          onClick={() => onChange(nextRange)}
          disabled={disableNext}
          className="flex h-8 w-8 items-center justify-center rounded-[9px] text-secondary transition-colors hover:bg-surface hover:text-primary disabled:cursor-not-allowed disabled:opacity-35"
          aria-label="Période suivante"
        >
          <ArrowRight size={14} />
        </button>
      </div>
      <div className="flex flex-wrap items-center rounded-[12px] bg-surface-soft p-1">
        {MODES.map((mode) => (
          <button
            key={mode.value}
            type="button"
            onClick={() => onChange(currentPeriod(mode.value))}
            className={cn(
              'h-8 rounded-[9px] px-3 text-[12px] font-medium transition-colors',
              value.mode === mode.value && value.isCurrent
                ? 'bg-accent text-white shadow-sm'
                : 'text-secondary hover:bg-surface hover:text-primary',
            )}
          >
            {mode.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export function ExportButtons({
  onJson,
  onPdf,
}: {
  onJson: () => void
  onPdf: () => void
}) {
  return (
    <div className="flex items-center gap-2">
      <Button type="button" size="sm" variant="secondary" onClick={onJson}>
        Export JSON
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onPdf}>
        Export PDF
      </Button>
    </div>
  )
}
