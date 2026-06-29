import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant = 'default' | 'blue' | 'green' | 'orange' | 'red' | 'gray'

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant
  children: ReactNode
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-[#f0f0f2] text-secondary',
  gray:    'bg-[#f0f0f2] text-secondary',
  blue:    'bg-accent/10 text-accent',
  green:   'bg-success/10 text-[#1a7a3a]',
  orange:  'bg-warning/10 text-[#c07000]',
  red:     'bg-danger/10 text-[#c0291f]',
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
