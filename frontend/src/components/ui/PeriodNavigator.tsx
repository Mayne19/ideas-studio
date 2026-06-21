import { ArrowLeft, ArrowRight, CalendarDays, Download } from 'lucide-react'
import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'
import { customPeriod, currentPeriod, isFuturePeriod, shiftPeriod, type PeriodMode, type PeriodRange } from '@/utils/periodNavigator'

const MODES: Array<{ value: PeriodMode; label: string }> = [
  { value: 'day', label: '1 jour' },
  { value: 'week', label: '1 semaine' },
  { value: 'month', label: '1 mois' },
  { value: 'quarter', label: '3 mois' },
  { value: 'semester', label: '6 mois' },
  { value: 'year', label: '1 an' },
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
      <div className="flex flex-wrap items-center gap-1 rounded-[12px] bg-surface-soft p-1">
        <span className="flex h-8 w-8 items-center justify-center text-tertiary">
          <CalendarDays size={14} />
        </span>
        <input
          type="date"
          value={value.startDate}
          onChange={(event) => onChange(customPeriod(event.target.value, value.endDate))}
          className="h-8 rounded-[9px] bg-surface px-2 text-[12px] text-secondary outline-none"
          aria-label="Date de début"
        />
        <input
          type="date"
          value={value.endDate}
          onChange={(event) => onChange(customPeriod(value.startDate, event.target.value))}
          className="h-8 rounded-[9px] bg-surface px-2 text-[12px] text-secondary outline-none"
          aria-label="Date de fin"
        />
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
      <Button type="button" size="sm" variant="secondary" icon={<Download size={13} />} onClick={onJson}>
        Export JSON
      </Button>
      <Button type="button" size="sm" variant="secondary" icon={<Download size={13} />} onClick={onPdf}>
        Export PDF
      </Button>
    </div>
  )
}
