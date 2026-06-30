import { cn } from '@/utils/cn'

type ToggleSwitchProps = {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  label?: string
  description?: string
  ariaLabel?: string
}

export default function ToggleSwitch({ checked, onChange, disabled = false, label, description, ariaLabel }: ToggleSwitchProps) {
  return (
    <div className={cn('flex items-start gap-3', disabled && 'opacity-50')}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={ariaLabel || label || 'Activer ou désactiver'}
        disabled={disabled}
        onClick={() => { if (!disabled) onChange(!checked) }}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (!disabled) onChange(!checked) } }}
        className={cn(
          'relative inline-flex h-[22px] w-[38px] shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:cursor-not-allowed',
          checked ? 'bg-accent' : 'bg-gray-300 dark:bg-gray-600',
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            'pointer-events-none inline-block h-[18px] w-[18px] rounded-full bg-white shadow-none ring-0 transition-transform duration-200 ease-in-out',
            checked ? 'translate-x-4' : 'translate-x-0',
          )}
        />
      </button>
      {(label || description) && (
        <div className="flex flex-col">
          {label && <span className="text-[14px] font-medium text-primary">{label}</span>}
          {description && <span className="text-[12px] text-tertiary">{description}</span>}
        </div>
      )}
    </div>
  )
}
