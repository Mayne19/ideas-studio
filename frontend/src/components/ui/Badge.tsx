import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant = 'default' | 'blue' | 'green' | 'orange' | 'red' | 'gray'

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant
  children: ReactNode
}

const variants: Record<BadgeVariant, string> = {
  default: 'border-[#e5e5e5] bg-[#f4f4f5] text-[#52525b]',
  gray:    'border-[#e5e5e5] bg-[#f4f4f5] text-[#52525b]',
  blue:    'border-[#dbeafe] bg-[#eff6ff] text-[#0b6bff]',
  green:   'border-[#bbf7d0] bg-[#dcfce7] text-[#128a3b]',
  orange:  'border-[#fed7aa] bg-[#ffedd5] text-[#c2410c]',
  red:     'border-[#fecaca] bg-[#fee2e2] text-[#dc2626]',
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
