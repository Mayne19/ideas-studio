import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export function TableRoot({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'w-full overflow-x-auto rounded-[12px] border-2 border-border bg-transparent',
        className,
      )}
      {...props}
    />
  )
}

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <table
      className={cn('w-full border-collapse text-[13px]', className)}
      {...props}
    />
  )
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn('border-b border-border/40', className)}
      {...props}
    />
  )
}

export function TableBody({
  bordered,
  className,
  ...props
}: HTMLAttributes<HTMLTableSectionElement> & { bordered?: boolean }) {
  return (
    <tbody
      className={cn(bordered && 'divide-y divide-border/30', className)}
      {...props}
    />
  )
}

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn('transition-colors hover:bg-surface-soft', className)}
      {...props}
    />
  )
}

export function TableHead({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'px-3 py-2.5 text-left text-[11px] font-medium uppercase tracking-wide text-tertiary',
        'first:pl-4 last:pr-4',
        className,
      )}
      {...props}
    />
  )
}

export function TableCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn(
        'px-3 py-3 align-middle text-[13px] text-primary',
        'first:pl-4 last:pr-4',
        className,
      )}
      {...props}
    />
  )
}
