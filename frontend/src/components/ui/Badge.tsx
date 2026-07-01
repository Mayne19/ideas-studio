import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant = 'default' | 'blue' | 'green' | 'orange' | 'red' | 'gray'

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant
  children: ReactNode
}

const variants: Record<BadgeVariant, string> = {
  default: 'border-border bg-surface-soft text-secondary',
  gray:    'border-border bg-surface-soft text-secondary',
  blue:    'border-accent/20 bg-accent/8 text-accent',
  green:   'border-success/20 bg-success/8 text-success',
  orange:  'border-warning/20 bg-warning/8 text-warning',
  red:     'border-danger/20 bg-danger/8 text-danger',
}

export default function Badge({ variant = 'default', children, className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex h-5 items-center gap-1 rounded-full border px-2 py-0.5 text-[12px] font-medium leading-none [&_svg]:pointer-events-none [&_svg]:size-3 [&_svg]:shrink-0',
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
