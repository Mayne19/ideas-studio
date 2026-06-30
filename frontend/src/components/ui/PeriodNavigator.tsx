import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, ArrowRight, CalendarDays, Download } from '@/components/ui/hugeIcons'
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
  const [customOpen, setCustomOpen] = useState(false)
  const [customStart, setCustomStart] = useState(value.startDate)
  const [customEnd, setCustomEnd] = useState(value.endDate)
  const customRef = useRef<HTMLDivElement>(null)

  const nextRange = shiftPeriod(value, 1)
  const disableNext = isFuturePeriod(nextRange)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (customRef.current && !customRef.current.contains(e.target as Node)) setCustomOpen(false)
    }
    if (customOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [customOpen])

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
      <div className="relative flex items-center rounded-[12px] bg-surface-soft p-1" ref={customRef}>
        <button
          type="button"
          onClick={() => { setCustomOpen(!customOpen); setCustomStart(value.startDate); setCustomEnd(value.endDate) }}
          className={cn(
            'flex h-8 items-center gap-1.5 rounded-[9px] px-3 text-[12px] font-medium transition-colors whitespace-nowrap',
            customOpen || !value.isCurrent ? 'bg-accent/10 text-accent' : 'text-secondary hover:bg-bg hover:text-primary',
          )}
        >
          <CalendarDays size={14} />
          Personnalisée
        </button>
        {customOpen && (
          <div className="absolute right-0 top-full z-50 mt-1.5 flex min-w-[260px] flex-col gap-2 rounded-[14px] border-2 border-border bg-transparent p-3.5 shadow-lg">
            <p className="text-[12px] font-medium uppercase tracking-wide text-secondary">Période personnalisée</p>
            <label className="text-[12px] font-medium text-primary">Date de début</label>
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="h-9 rounded-[10px] border border-border bg-surface-soft px-3 text-[14px] text-primary outline-none focus:border-accent"
            />
            <label className="text-[12px] font-medium text-primary">Date de fin</label>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="h-9 rounded-[10px] border border-border bg-surface-soft px-3 text-[14px] text-primary outline-none focus:border-accent"
            />
            <div className="mt-0.5 flex gap-2">
              <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setCustomOpen(false)}>Annuler</Button>
              <Button size="sm" className="flex-1 justify-center" onClick={() => { onChange(customPeriod(customStart, customEnd)); setCustomOpen(false) }}>Appliquer</Button>
            </div>
          </div>
        )}
      </div>
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
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div className={cn('relative', className)} ref={ref}>
      <Button type="button" size="sm" variant="secondary" icon={<Download size={13} />} onClick={() => setOpen(!open)}>
        Exporter
      </Button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 min-w-[175px] overflow-hidden rounded-[12px] border-2 border-border bg-transparent p-1 shadow-lg">
          <button type="button" onClick={() => { onJson(); setOpen(false) }} className="flex w-full items-center gap-2 rounded-[9px] px-3 py-2 text-[14px] text-primary transition-colors hover:bg-surface-soft">
            Exporter en JSON
          </button>
          <button type="button" onClick={() => { onPdf(); setOpen(false) }} className="flex w-full items-center gap-2 rounded-[9px] px-3 py-2 text-[14px] text-primary transition-colors hover:bg-surface-soft">
            Exporter en PDF
          </button>
        </div>
      )}
    </div>
  )
}
