import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from '@/components/ui/hugeIcons'
import { cn } from '@/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
}

/* Geist button spec (vercel.com/design.md):
   primary  = gray-1000 fill + inverted text (dark↔light flips in dark mode)
   secondary = surface fill + border
   ghost     = no fill, text-secondary, hover surface
   danger    = red fill + white text
   radius    = 6px (controls)
   height    = 32px/36px/40px (sm/md/lg)                                      */
const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-bg hover:opacity-90 active:opacity-80',
  secondary:
    'bg-surface-soft text-primary border border-border hover:bg-surface-muted active:bg-surface-muted',
  ghost:
    'bg-transparent text-secondary hover:bg-surface-soft hover:text-primary active:bg-surface-muted',
  danger:
    'bg-danger text-white hover:opacity-90 active:opacity-80',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-[6px]',
  md: 'h-9 px-4 text-[14px] gap-2 rounded-[6px]',
  lg: 'h-10 px-5 text-[14px] gap-2 rounded-[6px]',
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
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30 focus-visible:ring-offset-1',
        'disabled:opacity-50 disabled:cursor-not-allowed',
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
