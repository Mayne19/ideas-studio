import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from '@/components/ui/hugeIcons'
import { cn } from '@/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg' | 'icon'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
}

const variants: Record<ButtonVariant, string> = {
  primary:
    'border border-brand bg-brand text-white hover:bg-brand active:opacity-85',
  secondary:
    'border-2 border-border bg-transparent text-primary hover:bg-surface-soft active:bg-surface-muted',
  ghost:
    'border border-transparent bg-transparent text-primary hover:bg-surface-soft active:bg-surface-muted',
  danger:
    'border border-danger bg-danger text-white hover:opacity-90 active:opacity-80',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-10 px-3.5 text-[14px] gap-1.5 rounded-[8px]',
  md: 'h-10 px-4 text-[15px] gap-2 rounded-[8px]',
  lg: 'h-10 px-5 text-[15px] gap-2 rounded-[8px]',
  icon: 'h-10 w-10 rounded-[8px]',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, icon, children, className, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'shadow-none',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <Loader2 className="animate-spin" size={14} />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children}
    </button>
  )
})

export default Button
