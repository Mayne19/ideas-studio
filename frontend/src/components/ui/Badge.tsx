import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant = 'default' | 'blue' | 'green' | 'orange' | 'red' | 'gray'

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant
  children: ReactNode
}

/* Geist badge: pill shape (9999px per spec), semantic color tokens,
   no hardcoded hex — all values from --ds-* scale mapped via @theme  */
const variants: Record<BadgeVariant, string> = {
  default: 'bg-surface-soft text-secondary border border-border',
  gray:    'bg-surface-soft text-secondary border border-border',
  blue:    'bg-brand-soft text-accent border border-accent/20',
  green:   'bg-success/10 text-success border border-success/20',
  orange:  'bg-warning/10 text-warning border border-warning/20',
  red:     'bg-danger/10 text-danger border border-danger/20',
}

export default function Badge({ variant = 'default', children, className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
