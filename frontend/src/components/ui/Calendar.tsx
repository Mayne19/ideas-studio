import { DayPicker } from 'react-day-picker'
import { ChevronLeft, ChevronRight } from '@/components/ui/hugeIcons'
import { cn } from '@/utils/cn'

type CalendarProps = React.ComponentProps<typeof DayPicker>

export function Calendar({ className, classNames, showOutsideDays = true, ...props }: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn('p-3', className)}
      classNames={{
        months: 'flex gap-6',
        month: 'flex flex-col gap-3',
        month_caption: 'flex items-center justify-center relative h-8',
        caption_label: 'text-[13px] font-semibold text-primary',
        nav: 'flex items-center absolute inset-x-0 top-0 h-8',
        button_previous: 'absolute left-0 flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary transition-colors hover:bg-surface-soft hover:text-primary',
        button_next: 'absolute right-0 flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary transition-colors hover:bg-surface-soft hover:text-primary',
        month_grid: 'w-full border-collapse',
        weekdays: 'flex',
        weekday: 'flex-1 text-center text-[11px] font-medium text-tertiary py-1',
        week: 'flex mt-1',
        day: 'flex-1 text-center relative p-0',
        day_button: cn(
          'mx-auto flex h-8 w-8 items-center justify-center rounded-full text-[13px] font-medium text-primary transition-colors',
          'hover:bg-surface-soft',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40',
        ),
        selected: '[&>button]:bg-accent [&>button]:text-white [&>button]:hover:bg-accent/90',
        today: '[&>button]:font-bold [&>button]:text-accent',
        outside: '[&>button]:text-tertiary [&>button]:opacity-50',
        disabled: '[&>button]:opacity-30 [&>button]:cursor-not-allowed',
        range_start: '[&>button]:bg-accent [&>button]:text-white [&>button]:rounded-full',
        range_end: '[&>button]:bg-accent [&>button]:text-white [&>button]:rounded-full',
        range_middle: 'bg-accent/10 [&>button]:text-accent [&>button]:hover:bg-transparent rounded-none',
        hidden: 'invisible',
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) =>
          orientation === 'left' ? <ChevronLeft size={14} /> : <ChevronRight size={14} />,
      }}
      {...props}
    />
  )
}
