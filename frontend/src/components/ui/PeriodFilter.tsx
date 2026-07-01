import { cn } from '@/utils/cn'

export type PeriodOption<T extends string = string> = {
  value: T
  label: string
}

type PeriodFilterProps<T extends string> = {
  options: PeriodOption<T>[]
  value: T
  onChange: (value: T) => void
  onPrevious?: () => void
  onNext?: () => void
  onToday?: () => void
}

export default function PeriodFilter<T extends string>({ options, value, onChange, onPrevious, onNext, onToday }: PeriodFilterProps<T>) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {(onPrevious || onNext || onToday) && (
        <div className="flex overflow-hidden rounded-[10px] border border-border bg-transparent">
          {onPrevious && <button type="button" onClick={onPrevious} className="px-2.5 py-1.5 text-[12px] font-medium text-secondary hover:bg-surface-soft">Préc.</button>}
          {onToday && <button type="button" onClick={onToday} className="border-x border-border px-2.5 py-1.5 text-[12px] font-medium text-secondary hover:bg-surface-soft">Aujourd’hui</button>}
          {onNext && <button type="button" onClick={onNext} className="px-2.5 py-1.5 text-[12px] font-medium text-secondary hover:bg-surface-soft">Suiv.</button>}
        </div>
      )}
      <div className="flex overflow-hidden rounded-[10px] border border-border bg-transparent">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'px-3 py-1.5 text-[12px] font-medium transition-colors',
              value === option.value
                ? 'bg-accent text-white'
                : 'text-secondary hover:bg-surface-soft hover:text-primary',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
