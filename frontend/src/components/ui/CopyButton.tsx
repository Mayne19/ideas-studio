import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/utils/cn'

type CopyButtonProps = {
  value: string
  label?: string
  className?: string
  disabled?: boolean
}

export default function CopyButton({ value, label = 'Copier', className, disabled = false }: CopyButtonProps) {
  const [state, setState] = useState<'idle' | 'copied' | 'error'>('idle')

  async function handleCopy() {
    if (disabled || !value) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value)
      } else {
        const el = document.createElement('textarea')
        el.value = value
        document.body.appendChild(el)
        el.select()
        const copied = document.execCommand('copy')
        document.body.removeChild(el)
        if (!copied) throw new Error('copy failed')
      }
      setState('copied')
      setTimeout(() => setState('idle'), 2000)
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 2000)
    }
  }

  const isCopied = state === 'copied'
  const isError = state === 'error'

  return (
    <button
      onClick={handleCopy}
      disabled={disabled || !value}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[8px] px-3 py-1.5',
        'text-[12px] font-medium transition-all duration-150',
        disabled || !value
          ? 'cursor-not-allowed bg-[#f0f0f2] text-tertiary opacity-60'
          : isError
            ? 'bg-danger/10 text-danger'
            : isCopied
          ? 'bg-success/10 text-[#1a7a3a]'
          : 'bg-[#f0f0f2] text-secondary hover:bg-[#e5e5e7] hover:text-primary',
        className,
      )}
      aria-label={isError ? 'Erreur de copie' : isCopied ? 'Copié !' : label}
    >
      {isCopied ? <Check size={12} /> : <Copy size={12} />}
      {isError ? 'Erreur' : isCopied ? 'Copié !' : label}
    </button>
  )
}
