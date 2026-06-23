import { Loader2 } from '@/components/ui/hugeIcons'
import { MayneSkeleton } from '@mayne/ui-kit/ui'
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
      <div className="flex w-44 flex-col gap-2 opacity-70">
        <MayneSkeleton width="100%" height={8} radius={999} />
        <MayneSkeleton width="68%" height={8} radius={999} />
      </div>
    </div>
  )
}
