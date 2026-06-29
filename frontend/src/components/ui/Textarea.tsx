import { forwardRef } from 'react'
import type { TextareaHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  error?: string
  hint?: string
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, hint, className, id, ...props },
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
      <textarea
        ref={ref}
        id={inputId}
        className={cn(
          'w-full rounded-[8px] border border-border bg-surface px-3.5 py-2.5',
          'text-[14px] text-primary placeholder:text-tertiary',
          'outline-none transition-all duration-150 resize-none',
          'hover:border-border-strong',
          'focus:border-accent focus:ring-2 focus:ring-accent/10',
          error && 'border-danger focus:border-danger focus:ring-danger/10',
          className,
        )}
        {...props}
      />
      {error && <p className="text-[12px] text-danger">{error}</p>}
      {hint && !error && <p className="text-[12px] text-tertiary">{hint}</p>}
    </div>
  )
})

export default Textarea
