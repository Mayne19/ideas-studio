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
  blue:    'border-blue-200 bg-blue-50 text-blue-700',
  green:   'border-green-200 bg-green-50 text-green-700',
  orange:  'border-amber-200 bg-amber-50 text-amber-700',
  red:     'border-red-200 bg-red-50 text-red-700',
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
