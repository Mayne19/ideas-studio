import { cn } from '@/utils/cn'

type SkeletonProps = {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-[6px] bg-surface-muted',
        className,
      )}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-[8px] border border-border bg-bg p-5 shadow-card">
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
