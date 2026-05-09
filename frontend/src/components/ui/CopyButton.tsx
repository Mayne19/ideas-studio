import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/utils/cn'

type CopyButtonProps = {
  value: string
  label?: string
  className?: string
}

export default function CopyButton({ value, label = 'Copier', className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback for non-secure contexts
      const el = document.createElement('textarea')
      el.value = value
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[8px] px-3 py-1.5',
        'text-[12px] font-medium transition-all duration-150',
        copied
          ? 'bg-success/10 text-[#1a7a3a]'
          : 'bg-[#f0f0f2] text-secondary hover:bg-[#e5e5e7] hover:text-primary',
        className,
      )}
      aria-label={copied ? 'Copié !' : label}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? 'Copié !' : label}
    </button>
  )
}
