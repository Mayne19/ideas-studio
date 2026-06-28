import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { X } from '@/components/ui/hugeIcons'
import { cn } from '@/utils/cn'

type DrawerProps = {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  side?: 'right' | 'left'
  className?: string
}

export default function Drawer({
  open, onClose, title, children, side = 'right', className,
}: DrawerProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog">
      <div
        className="absolute inset-0 bg-black/25 backdrop-blur-[2px] animate-in fade-in duration-200"
        onClick={onClose}
      />
      <div
        className={cn(
          'absolute top-0 h-full w-full max-w-md bg-bg border-l border-border shadow-float animate-in duration-200',
          side === 'right' ? 'right-0 slide-in-from-right-4' : 'left-0 slide-in-from-left-4',
          className,
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="text-[15px] font-semibold text-primary">{title}</h2>
            <button
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-[6px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
              aria-label="Fermer"
            >
              <X size={15} />
            </button>
          </div>
        )}
        <div className="overflow-y-auto h-[calc(100%-57px)] p-6">{children}</div>
      </div>
    </div>
  )
}
