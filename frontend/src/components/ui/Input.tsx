import { forwardRef } from 'react'
import type { InputHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  error?: string
  hint?: string
}

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
          className="text-[14px] font-medium text-primary"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={cn(
          'h-10 w-full rounded-[8px] border-2 border-border bg-transparent px-3.5',
          'text-[15px] text-primary placeholder:text-tertiary',
          'outline-none transition-all duration-150',
          'hover:border-border-strong',
          'focus:border-accent focus:ring-2 focus:ring-accent/10',
          error && 'border-danger focus:border-danger focus:ring-danger/10',
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
