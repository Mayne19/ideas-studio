import { Loader2, Check, AlertCircle } from '@/components/ui/hugeIcons'

type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export default function AutosaveIndicator({ status }: { status: AutosaveStatus }) {
  if (status === 'idle') return null

  return (
    <div className="flex items-center gap-1.5 text-[12px]">
      {status === 'saving' && (
        <>
          <Loader2 size={12} className="animate-spin text-tertiary" />
          <span className="text-tertiary">Enregistrement...</span>
        </>
      )}
      {status === 'saved' && (
        <>
          <Check size={12} className="text-success" />
          <span className="text-success">Enregistré</span>
        </>
      )}
      {status === 'error' && (
        <>
          <AlertCircle size={12} className="text-danger" />
          <span className="text-danger">Erreur d'enregistrement</span>
        </>
      )}
    </div>
  )
}
