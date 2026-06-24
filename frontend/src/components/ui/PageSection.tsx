import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type PageSectionProps = {
  title: string
  description?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export default function PageSection({ title, description, action, children, className }: PageSectionProps) {
  return (
    <section className={cn('flex flex-col gap-3', className)}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[12px] font-semibold text-secondary uppercase tracking-wide">{title}</h2>
          {description && (
            <p className="mt-0.5 text-[12px] text-tertiary">{description}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </section>
  )
}
