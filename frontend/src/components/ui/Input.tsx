import { forwardRef } from 'react'
import type { InputHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  error?: string
  hint?: string
}

/* Geist input: 6px radius, 40px height, thin border, blue focus ring */
const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, className, id, ...props },
  ref,
) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={inputId}
          className="text-[13px] font-medium text-primary"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={cn(
          'h-10 w-full rounded-[6px] border border-border bg-bg px-3',
          'text-[14px] text-primary placeholder:text-tertiary',
          'outline-none transition-all duration-150',
          'hover:border-border-strong',
          'focus:border-accent focus:ring-2 focus:ring-accent/20',
          error && 'border-danger focus:border-danger focus:ring-danger/20',
          className,
        )}
        {...props}
      />
      {error && (
        <p className="text-[12px] text-danger">{error}</p>
      )}
      {hint && !error && (
        <p className="text-[12px] text-tertiary">{hint}</p>
      )}
    </div>
  )
})

export default Input
