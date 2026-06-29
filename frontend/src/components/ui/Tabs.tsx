import { cn } from '@/utils/cn'

type TabItem = {
  label: string
  value: string
}

type TabsProps = {
  items: TabItem[]
  value: string
  onChange: (value: string) => void
  className?: string
}

export default function Tabs({ items, value, onChange, className }: TabsProps) {
  return (
    <div
      className={cn(
        'inline-flex rounded-[10px] bg-surface-soft p-1 gap-0.5',
        className,
      )}
      role="tablist"
    >
      {items.map((item) => (
        <button
          key={item.value}
          role="tab"
          aria-selected={value === item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            'rounded-[8px] px-3.5 py-1.5 text-[13px] font-medium transition-all duration-150',
            value === item.value
              ? 'bg-surface text-primary shadow-none'
              : 'text-secondary hover:text-primary',
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}
