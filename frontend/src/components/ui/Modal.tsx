import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { X } from '@/components/ui/hugeIcons'
import { cn } from '@/utils/cn'

type ModalSize = 'sm' | 'md' | 'lg'

type ModalProps = {
  open: boolean
  onClose: () => void
  title?: string
  size?: ModalSize
  children: ReactNode
}

const sizes: Record<ModalSize, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
}

export default function Modal({ open, onClose, title, size = 'md', children }: ModalProps) {
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      aria-modal="true"
      role="dialog"
    >
      <div
        className="absolute inset-0 bg-black/25 backdrop-blur-[2px] animate-in fade-in duration-200"
        onClick={onClose}
      />
      <div
        className={cn(
          'relative w-full rounded-[12px] border border-border bg-surface shadow-none',
          'animate-in zoom-in-95 fade-in duration-200',
          sizes[size],
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="text-[15px] font-semibold text-primary">{title}</h2>
            <button
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-full text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
              aria-label="Fermer"
            >
              <X size={15} />
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
