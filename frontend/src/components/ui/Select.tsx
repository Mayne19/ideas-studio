import { forwardRef } from 'react'
import type { SelectHTMLAttributes } from 'react'
import { ChevronDown } from '@/components/ui/hugeIcons'
import { cn } from '@/utils/cn'

type SelectOption = {
  value: string
  label: string
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string
  error?: string
  hint?: string
  options: SelectOption[]
  placeholder?: string
}

/* Geist select: 6px radius, 40px height, thin border, blue focus ring */
const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, hint, options, placeholder, className, id, ...props },
  ref,
) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-[13px] font-medium text-primary">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={inputId}
          className={cn(
            'h-10 w-full appearance-none rounded-[6px] border border-border bg-bg px-3 pr-9',
            'text-[14px] text-primary',
            'outline-none transition-all duration-150 cursor-pointer',
            'hover:border-border-strong',
            'focus:border-accent focus:ring-2 focus:ring-accent/20',
            error && 'border-danger focus:border-danger focus:ring-danger/20',
            className,
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown
          size={15}
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-tertiary"
        />
      </div>
      {error && <p className="text-[12px] text-danger">{error}</p>}
      {hint && !error && <p className="text-[12px] text-tertiary">{hint}</p>}
    </div>
  )
})

export default Select
