import { AlertCircle } from '@/components/ui/hugeIcons'
import Button from './Button'
import { cn } from '@/utils/cn'

type ErrorStateProps = {
  title?: string
  message?: string
  onRetry?: () => void
  className?: string
}

export default function ErrorState({
  title = 'Une erreur est survenue',
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-danger/8 text-danger">
        <AlertCircle size={22} />
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-[15px] font-medium text-primary">{title}</p>
        {message && (
          <p className="max-w-xs text-[13px] text-secondary leading-relaxed">{message}</p>
        )}
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-1">
          Réessayer
        </Button>
      )}
    </div>
  )
}
