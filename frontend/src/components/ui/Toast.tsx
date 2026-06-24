/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { CheckCircle, AlertCircle, X } from '@/components/ui/hugeIcons'

type ToastVariant = 'success' | 'error' | 'info'

type ToastItem = {
  id: string
  variant: ToastVariant
  message: string
}

type ToastContextType = {
  toast: (variant: ToastVariant, message: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const toast = useCallback((variant: ToastVariant, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    setItems((prev) => [...prev, { id, variant, message }])
    setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const remove = (id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id))
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              'flex items-start gap-2.5 rounded-[14px] px-4 py-3 shadow-lg min-w-[280px] max-w-[400px] animate-in slide-in-from-right-4 fade-in duration-200',
              item.variant === 'success' && 'bg-[#e8f5e9] border border-success/20 text-[#1a7a3a]',
              item.variant === 'error' && 'bg-[#fef2f2] border border-danger/20 text-danger',
              item.variant === 'info' && 'bg-surface border border-border text-primary',
            )}
          >
            {item.variant === 'success' && <CheckCircle size={16} className="mt-0.5 shrink-0" />}
            {item.variant === 'error' && <AlertCircle size={16} className="mt-0.5 shrink-0" />}
            {item.variant === 'info' && <AlertCircle size={16} className="mt-0.5 shrink-0 text-accent" />}
            <p className="flex-1 text-[13px] leading-snug">{item.message}</p>
            <button onClick={() => remove(item.id)} className="shrink-0 opacity-60 hover:opacity-100 transition-opacity">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
