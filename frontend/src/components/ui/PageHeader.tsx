import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type PageHeaderProps = {
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export default function PageHeader({ title, description, action, className }: PageHeaderProps) {
  return (
    <div className={cn('mb-8 flex items-start justify-between gap-4', className)}>
      <div>
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">{title}</h1>
        {description && (
          <p className="mt-0.5 text-[14px] text-secondary">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
