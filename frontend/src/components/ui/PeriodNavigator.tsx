import { useState } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import type { DateRange } from 'react-day-picker'
import { ArrowLeft, ArrowRight, CalendarDays, Download } from '@/components/ui/hugeIcons'
import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/Popover'
import { Calendar } from '@/components/ui/Calendar'
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
  const [calRange, setCalRange] = useState<DateRange | undefined>(() => ({
    from: new Date(value.startDate),
    to: new Date(value.endDate),
  }))
  const [popoverOpen, setPopoverOpen] = useState(false)

  const nextRange = shiftPeriod(value, 1)
  const disableNext = isFuturePeriod(nextRange)

  function handleApply() {
    if (!calRange?.from) return
    const from = format(calRange.from, 'yyyy-MM-dd')
    const to = format(calRange.to ?? calRange.from, 'yyyy-MM-dd')
    onChange(customPeriod(from, to))
    setPopoverOpen(false)
  }

  function customLabel() {
    if (!calRange?.from) return 'Personnalisée'
    const from = format(calRange.from, 'd MMM', { locale: fr })
    if (!calRange.to) return from
    return `${from} – ${format(calRange.to, 'd MMM', { locale: fr })}`
  }

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {/* Presets - Left */}
      <div className="flex flex-wrap items-center rounded-[12px] bg-surface-soft p-1">
        {MODES.map((mode) => (
          <button
            key={mode.value}
            type="button"
            onClick={() => onChange(currentPeriod(mode.value))}
            className={cn(
              'h-8 rounded-[9px] px-2.5 text-[12px] font-medium transition-colors whitespace-nowrap',
              value.mode === mode.value && value.isCurrent
                ? 'bg-accent text-white shadow-none'
                : 'text-secondary hover:bg-bg hover:text-primary',
            )}
          >
            {mode.label}
          </button>
        ))}
      </div>

      {/* Navigation - Center */}
      <div className="flex items-center rounded-[12px] bg-surface-soft p-1">
        <button
          type="button"
          onClick={() => onChange(shiftPeriod(value, -1))}
          className="flex h-8 w-8 items-center justify-center rounded-[9px] text-secondary transition-colors hover:bg-bg hover:text-primary"
          aria-label="Période précédente"
        >
          <ArrowLeft size={14} />
        </button>
        <span className="min-w-[160px] px-2.5 text-center text-[12px] font-medium text-secondary">
          {value.label}
        </span>
        <button
          type="button"
          onClick={() => onChange(nextRange)}
          disabled={disableNext}
          className="flex h-8 w-8 items-center justify-center rounded-[9px] text-secondary transition-colors hover:bg-bg hover:text-primary disabled:cursor-not-allowed disabled:opacity-35"
          aria-label="Période suivante"
        >
          <ArrowRight size={14} />
        </button>
      </div>

      {/* Custom - Right */}
      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <div className="flex items-center rounded-[12px] bg-surface-soft p-1">
            <button
              type="button"
              className={cn(
                'flex h-8 items-center gap-1.5 rounded-[9px] px-3 text-[12px] font-medium transition-colors whitespace-nowrap',
                popoverOpen || !value.isCurrent ? 'bg-accent/10 text-accent' : 'text-secondary hover:bg-bg hover:text-primary',
              )}
            >
              <CalendarDays size={14} />
              {!value.isCurrent ? customLabel() : 'Personnalisée'}
            </button>
          </div>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-auto p-0">
          <Calendar
            mode="range"
            defaultMonth={calRange?.from}
            selected={calRange}
            onSelect={setCalRange}
            numberOfMonths={2}
          />
          <div className="flex gap-2 border-t border-border p-3">
            <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setPopoverOpen(false)}>Annuler</Button>
            <Button size="sm" className="flex-1 justify-center" onClick={handleApply}>Appliquer</Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}

export function ExportButtons({
  onJson,
  onPdf,
  className,
}: {
  onJson: () => void
  onPdf: () => void
  className?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button type="button" size="sm" variant="secondary" icon={<Download size={13} />} className={className}>
          Exporter
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="min-w-[175px] p-1">
          <button type="button" onClick={() => { onJson(); setOpen(false) }} className="flex w-full items-center gap-2 rounded-[9px] px-3 py-2 text-[14px] text-primary transition-colors hover:bg-surface-soft">
            Exporter en JSON
          </button>
          <button type="button" onClick={() => { onPdf(); setOpen(false) }} className="flex w-full items-center gap-2 rounded-[9px] px-3 py-2 text-[14px] text-primary transition-colors hover:bg-surface-soft">
            Exporter en PDF
          </button>
      </PopoverContent>
    </Popover>
  )
}
