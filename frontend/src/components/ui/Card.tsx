import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/utils/cn'

type CardPadding = 'none' | 'sm' | 'md' | 'lg'

type CardProps = HTMLAttributes<HTMLDivElement> & {
  padding?: CardPadding
  children: ReactNode
}

const paddings: Record<CardPadding, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6',
}

/* Geist card: 8px radius, thin border, subtle raised shadow */
export function Card({ padding = 'md', children, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-[8px] bg-surface border border-border shadow-card',
        paddings[padding],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

type CardHeaderProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
}

export function CardHeader({ children, className, ...props }: CardHeaderProps) {
  return (
    <div className={cn('mb-4', className)} {...props}>
      {children}
    </div>
  )
}

type CardTitleProps = HTMLAttributes<HTMLHeadingElement> & {
  children: ReactNode
}

export function CardTitle({ children, className, ...props }: CardTitleProps) {
  return (
    <h3 className={cn('text-[14px] font-semibold text-primary', className)} {...props}>
      {children}
    </h3>
  )
}
