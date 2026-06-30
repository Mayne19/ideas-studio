import { cn } from '@/utils/cn'
import type { HTMLAttributes } from 'react'

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-[6px] bg-[#e8e8ea]',
        className,
      )}
      {...props}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-[8px] border-2 border-border bg-transparent p-5 shadow-none">
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
