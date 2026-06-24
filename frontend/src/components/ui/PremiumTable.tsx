import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'
import ErrorState from '@/components/ui/ErrorState'
import EmptyState from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'

type ColumnDef = {
  key: string
  header: ReactNode
  className?: string
  hide?: 'mobile' | 'tablet' | never
}

type PremiumTableProps = {
  columns: ColumnDef[]
  data: Record<string, unknown>[]
  status?: 'loading' | 'success' | 'error'
  onRetry?: () => void
  emptyTitle?: string
  emptyDescription?: string
  emptyIcon?: ReactNode
  emptyAction?: { label: string; onClick: () => void }
  errorMessage?: string
  skeletonRows?: number
  renderRow: (item: Record<string, unknown>, index: number) => ReactNode
  className?: string
}

const hideMap = {
  mobile: 'hidden lg:block',
  tablet: 'hidden xl:block',
}

export default function PremiumTable({
  columns, data, status = 'success', onRetry,
  emptyTitle, emptyDescription, emptyIcon, emptyAction,
  errorMessage, skeletonRows = 6, renderRow, className,
}: PremiumTableProps) {
  if (status === 'loading') {
    return (
      <div className={cn('flex flex-col gap-2', className)}>
        {Array.from({ length: skeletonRows }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-[12px]" />
        ))}
      </div>
    )
  }

  if (status === 'error') {
    return (
      <ErrorState
        message={errorMessage ?? 'Impossible de charger les données.'}
        onRetry={onRetry}
      />
    )
  }

  if (status === 'success' && data.length === 0) {
    return (
      <EmptyState
        icon={emptyIcon}
        title={emptyTitle ?? 'Aucune donnée'}
        description={emptyDescription}
        action={emptyAction}
      />
    )
  }

  return (
    <div className={cn('flex flex-col', className)}>
      <div className={cn('hidden gap-2.5 px-3 pb-1.5 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid')}
        style={{ gridTemplateColumns: columns.map((col) => col.className ?? '1fr').join(' ') }}
      >
        {columns.map((col) => (
          <div key={col.key} className={cn(col.hide ? hideMap[col.hide] : '')}>
            {col.header}
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-1">
        {data.map((item, i) => renderRow(item, i))}
      </div>
    </div>
  )
}
