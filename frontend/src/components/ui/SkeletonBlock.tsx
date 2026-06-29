import { cn } from '@/utils/cn'
import { Skeleton } from '@/components/ui/Skeleton'

type SkeletonBlockProps = {
  variant?: 'card' | 'table-row' | 'text-block' | 'metric'
  className?: string
}

export function SkeletonBlock({ variant = 'text-block', className }: SkeletonBlockProps) {
  if (variant === 'card') {
    return (
      <div className={cn('rounded-[8px] border border-border bg-surface p-5', className)}>
        <div className="flex flex-col gap-3">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
        </div>
      </div>
    )
  }

  if (variant === 'table-row') {
    return (
      <div className={cn('flex items-center gap-3 rounded-[8px] bg-surface px-3 py-3', className)}>
        <Skeleton className="h-4 flex-1" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-6 w-16 rounded-[8px]" />
      </div>
    )
  }

  if (variant === 'metric') {
    return (
      <div className={cn('rounded-[8px] border border-border bg-surface p-4 flex flex-col gap-2', className)}>
        <Skeleton className="h-8 w-8 rounded-[8px]" />
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-3 w-16" />
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}
