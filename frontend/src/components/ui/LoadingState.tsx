import { Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'

type LoadingStateProps = {
  label?: string
  className?: string
}

export default function LoadingState({ label = 'Chargement…', className }: LoadingStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16', className)}>
      <Loader2 size={24} className="animate-spin text-tertiary" />
      <p className="text-[13px] text-tertiary">{label}</p>
    </div>
  )
}
