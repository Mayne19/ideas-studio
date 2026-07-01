import type { ReactNode } from 'react'
import Button from './Button'
import { cn } from '@/utils/cn'

type EmptyStateProps = {
  icon?: ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export default function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      {icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-[16px] border-2 border-border bg-transparent text-tertiary">
          {icon}
        </div>
      )}
      <div className="flex flex-col gap-1">
        <p className="text-[15px] font-medium text-primary">{title}</p>
        {description && (
          <p className="max-w-xs text-[14px] text-secondary leading-relaxed">{description}</p>
        )}
      </div>
      {action && (
        <Button size="sm" onClick={action.onClick} className="mt-1">
          {action.label}
        </Button>
      )}
    </div>
  )
}
