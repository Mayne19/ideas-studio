import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type ToolbarProps = {
  children: ReactNode
  className?: string
}

export default function Toolbar({ children, className }: ToolbarProps) {
  return (
    <div className={cn('mb-4 flex flex-wrap items-center gap-2', className)}>
      {children}
    </div>
  )
}
