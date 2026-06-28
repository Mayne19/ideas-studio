import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant = 'default' | 'blue' | 'green' | 'amber' | 'orange' | 'red' | 'gray'

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant
  children: ReactNode
  icon?: ReactNode
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-surface text-secondary border-border',
  gray:    'bg-surface text-secondary border-border',
  blue:    'bg-brand-soft text-accent border-accent/20',
  green:   'bg-success/10 text-success border-success/20',
  amber:   'bg-warning/10 text-warning border-warning/25',
  orange:  'bg-warning/10 text-warning border-warning/25',
  red:     'bg-danger/10 text-danger border-danger/20',
}

export default function Badge({ variant = 'default', icon, children, className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex h-6 items-center gap-1 rounded-full border px-2 text-[11px] font-medium leading-none',
        variants[variant],
        className,
      )}
      {...props}
    >
      {icon && <span className="flex shrink-0 items-center">{icon}</span>}
      {children}
    </span>
  )
}
