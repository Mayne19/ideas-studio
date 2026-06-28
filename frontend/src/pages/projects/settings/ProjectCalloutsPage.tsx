import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Import, Pencil, Plus, Trash2 } from '@/components/ui/hugeIcons'

import {
  createCalloutTemplate,
  deleteCalloutTemplate,
  listCalloutTemplates,
  syncCalloutTemplates,
  updateCalloutTemplate,
  type CreateCalloutTemplatePayload,
  type UpdateCalloutTemplatePayload,
} from '@/api/callouts'
import type { CalloutTemplate } from '@/types'
import Button from '@/components/ui/Button'
import ConfirmModal from '@/components/ui/ConfirmModal'
import FormCard from '@/components/ui/FormCard'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import ColorPickerField from '@/components/ui/ColorPickerField'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import { DEFAULT_ACCENT_COLOR, normalizeHexColor } from '@/lib/colors'
import { deriveCalloutColors, slugifyCalloutLabel } from '@/lib/callouts'

type FormState = {
  label: string
  default_title: string
  primary_color: string
}

const DEFAULT_FORM: FormState = {
  label: '',
  default_title: '',
  primary_color: DEFAULT_ACCENT_COLOR,
}

export default function ProjectCalloutsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [callouts, setCallouts] = useState<CalloutTemplate[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CalloutTemplate | null>(null)
  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<CalloutTemplate | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    if (!projectId) return
    setStatus('loading')
    listCalloutTemplates(projectId)
      .then((items) => {
        setCallouts(items)
        setStatus('success')
      })
      .catch(() => setStatus('error'))
  }, [projectId])

  useEffect(() => {
    Promise.resolve().then(() => load())
  }, [load])

  function openCreate() {
    setEditing(null)
    setForm(DEFAULT_FORM)
    setFormError('')
    setModalOpen(true)
  }

  function openEdit(callout: CalloutTemplate) {
    setEditing(callout)
    setForm({
      label: callout.label,
      default_title: callout.default_title ?? '',
      primary_color: normalizeHexColor(callout.color_border ?? callout.color_text ?? callout.color_background, DEFAULT_ACCENT_COLOR),
    })
    setFormError('')
    setModalOpen(true)
  }

  function setField(field: keyof FormState) {
    return (event: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }))
    }
  }

  async function handleSync() {
    if (!projectId) return
    setSyncing(true)
    setSyncMessage('')
    try {
      const result = await syncCalloutTemplates(projectId)
      setCallouts(result.callouts)
      setSyncMessage(result.message)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Synchronisation impossible.'
      setSyncMessage(msg)
      if (msg.includes('aucun domaine') || msg.includes('Aucun domaine') || msg.includes('Aucun site externe')) {
        setSyncMessage('Aucun site externe configuré pour synchroniser les callouts.')
      }
    } finally {
      setSyncing(false)
      window.setTimeout(() => setSyncMessage(''), 8000)
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId || !form.label.trim()) return
    setSaving(true)
    setFormError('')

    const primaryColor = normalizeHexColor(form.primary_color, DEFAULT_ACCENT_COLOR)

    const basePayload = {
      label: form.label.trim(),
      style: slugifyCalloutLabel(form.label),
      default_title: form.default_title.trim() || null,
      ...deriveCalloutColors(primaryColor),
      source: (editing?.source === 'imported' ? 'imported' : 'manual') as 'imported' | 'manual',
    }

    try {
      if (editing) {
        const payload: UpdateCalloutTemplatePayload = basePayload
        await updateCalloutTemplate(projectId, editing.id, payload)
      } else {
        const payload: CreateCalloutTemplatePayload = basePayload
        await createCalloutTemplate(projectId, payload)
      }
      setModalOpen(false)
      load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Enregistrement impossible.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!projectId || !deleteTarget) return
    setDeleting(true)
    try {
      await deleteCalloutTemplate(projectId, deleteTarget.id)
      setDeleteTarget(null)
      load()
    } catch (err) {
      setSyncMessage(err instanceof Error ? err.message : 'Suppression impossible.')
    } finally {
      setDeleting(false)
    }
  }

  if (status === 'loading') return <LoadingState />
  if (status === 'error') return <ErrorState onRetry={load} />

  return (
    <div className="flex flex-col gap-5">
      <FormCard
        title="Templates de callouts"
        description="Importez les encadrés du site connecté ou créez vos propres variantes pour l'éditeur."
        footer={
          <div className="flex items-center gap-3">
            {syncMessage && <span className="text-[12px] text-secondary">{syncMessage}</span>}
            <Button type="button" variant="secondary" size="sm" icon={<Import size={14} />} loading={syncing} onClick={handleSync}>
              Importer depuis le site
            </Button>
            <Button type="button" size="sm" icon={<Plus size={14} />} onClick={openCreate}>
              Créer un callout
            </Button>
          </div>
        }
      >
        {callouts.length === 0 ? (
          <div className="rounded-[8px] bg-surface px-4 py-5 text-[13px] text-secondary">
            Aucun callout configuré pour ce projet. Importez-les depuis le site connecté ou créez un template manuel.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {callouts.map((callout) => (
              <div key={callout.id} className="rounded-[8px] border border-border bg-surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[14px] font-semibold text-primary">{callout.label}</p>
                    <p className="mt-0.5 text-[12px] text-secondary">
                      Style {callout.style ?? '—'} · {callout.source === 'imported' ? 'Importé' : 'Manuel'}
                    </p>
                    {callout.default_title && (
                      <p className="mt-1 text-[12px] text-tertiary">Titre par défaut : {callout.default_title}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button type="button" onClick={() => openEdit(callout)} className="rounded-[6px] p-2 text-secondary hover:bg-surface-soft hover:text-primary">
                      <Pencil size={13} />
                    </button>
                    <button type="button" onClick={() => setDeleteTarget(callout)} className="rounded-[8px] p-2 text-secondary hover:bg-danger/10 hover:text-danger">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
                <div
                  className="mt-3 rounded-[8px] border px-3 py-2"
                  style={{
                    backgroundColor: callout.color_background ?? '#eff6ff',
                    borderColor: callout.color_border ?? '#3b82f6',
                    color: callout.color_text ?? '#1e3a8a',
                  }}
                >
                  <p className="text-[12px] font-semibold">{callout.default_title || callout.label}</p>
                  <p className="mt-1 text-[12px] opacity-85">Exemple de rendu du template dans l'éditeur.</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </FormCard>

      <Modal
        open={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title={editing ? 'Modifier le callout' : 'Créer un callout'}
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <p className="text-[13px] text-secondary">
            Créez un template simple pour l'éditeur. Les variantes de fond, bordure et texte sont dérivées automatiquement.
          </p>
          <Input label="Nom" value={form.label} onChange={setField('label')} required />
          <Input label="Titre par défaut" value={form.default_title} onChange={setField('default_title')} placeholder="À retenir" />
          <ColorPickerField
            label="Couleur principale"
            value={form.primary_color}
            onChange={(value) => setForm((prev) => ({ ...prev, primary_color: value }))}
          />
          <div
            className="rounded-[8px] border px-3 py-2"
            style={{
              backgroundColor: deriveCalloutColors(form.primary_color).color_background,
              borderColor: deriveCalloutColors(form.primary_color).color_border,
              color: deriveCalloutColors(form.primary_color).color_text,
            }}
          >
            <p className="text-[12px] font-semibold">{form.default_title || form.label || 'Aperçu du callout'}</p>
            <p className="mt-1 text-[12px] opacity-85">Le rendu est généré automatiquement à partir de votre couleur principale.</p>
          </div>
          {formError && <p className="text-[12px] text-danger">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setModalOpen(false)}>Annuler</Button>
            <Button type="submit" loading={saving}>{editing ? 'Mettre à jour' : 'Créer'}</Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={Boolean(deleteTarget)}
        onClose={() => !deleting && setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Supprimer ce callout ?"
        description="Le template sera retiré du projet s'il n'est pas déjà utilisé dans un article."
        confirmLabel="Supprimer"
        loading={deleting}
        variant="danger"
      />
    </div>
  )
}
