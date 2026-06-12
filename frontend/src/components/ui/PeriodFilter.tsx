import { cn } from '@/utils/cn'

export type PeriodOption<T extends string = string> = {
  value: T
  label: string
}

type PeriodFilterProps<T extends string> = {
  options: PeriodOption<T>[]
  value: T
  onChange: (value: T) => void
}

export default function PeriodFilter<T extends string>({ options, value, onChange }: PeriodFilterProps<T>) {
  return (
    <div className="flex overflow-hidden rounded-[10px] border border-border bg-surface">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            'px-3 py-1.5 text-[12px] font-medium transition-colors',
            value === option.value
              ? 'bg-accent text-white'
              : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
