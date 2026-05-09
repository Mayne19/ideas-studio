import Modal from './Modal'
import Button from './Button'

type ConfirmModalProps = {
  open: boolean
  onClose: () => void
  onConfirm: () => void | Promise<void>
  title: string
  description?: string
  confirmLabel?: string
  loading?: boolean
  variant?: 'danger' | 'primary'
}

export default function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirmer',
  loading = false,
  variant = 'danger',
}: ConfirmModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="sm">
      <div className="flex flex-col gap-5">
        {description && (
          <p className="text-[14px] text-secondary leading-relaxed">{description}</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={loading}>
            Annuler
          </Button>
          <Button
            variant={variant}
            size="sm"
            loading={loading}
            onClick={async () => {
              await onConfirm()
            }}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
