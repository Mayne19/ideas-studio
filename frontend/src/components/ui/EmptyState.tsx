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

/* Geist empty state: surface-soft icon container, 12px radius, neutral tones */
export default function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      {icon && (
        <div className="flex h-10 w-10 items-center justify-center rounded-[8px] bg-surface-soft border border-border text-tertiary">
          {icon}
        </div>
      )}
      <div className="flex flex-col gap-1">
        <p className="text-[14px] font-medium text-primary">{title}</p>
        {description && (
          <p className="max-w-xs text-[13px] text-secondary leading-relaxed">{description}</p>
        )}
      </div>
      {action && (
        <Button variant="secondary" size="sm" onClick={action.onClick} className="mt-1">
          {action.label}
        </Button>
      )}
    </div>
  )
}
