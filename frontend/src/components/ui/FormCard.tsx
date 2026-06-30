import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type FormCardProps = {
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  className?: string
}

export default function FormCard({ title, description, children, footer, className }: FormCardProps) {
  return (
    <div className={cn('rounded-[8px] border-2 border-border bg-transparent shadow-none', className)}>
      <div className="border-b border-border/40 px-6 py-5">
        <h3 className="text-[15px] font-semibold text-primary">{title}</h3>
        {description && (
          <p className="mt-0.5 text-[14px] text-secondary">{description}</p>
        )}
      </div>
      <div className="p-6">{children}</div>
      {footer && (
        <div className="flex items-center justify-end gap-2 border-t border-border/40 px-6 py-4">
          {footer}
        </div>
      )}
    </div>
  )
}
