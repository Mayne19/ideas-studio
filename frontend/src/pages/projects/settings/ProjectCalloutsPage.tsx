import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Import, Pencil, Plus, Trash2 } from 'lucide-react'

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
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'

type FormState = {
  label: string
  style: string
  default_title: string
  color_background: string
  color_border: string
  color_text: string
  icon: string
}

const DEFAULT_FORM: FormState = {
  label: '',
  style: 'info',
  default_title: '',
  color_background: '#eff6ff',
  color_border: '#3b82f6',
  color_text: '#1e3a8a',
  icon: '',
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
      style: callout.style ?? 'info',
      default_title: callout.default_title ?? '',
      color_background: callout.color_background ?? '#eff6ff',
      color_border: callout.color_border ?? '#3b82f6',
      color_text: callout.color_text ?? '#1e3a8a',
      icon: callout.icon ?? '',
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
      setSyncMessage(err instanceof Error ? err.message : 'Synchronisation impossible.')
    } finally {
      setSyncing(false)
      window.setTimeout(() => setSyncMessage(''), 5000)
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId || !form.label.trim()) return
    setSaving(true)
    setFormError('')

    const basePayload = {
      label: form.label.trim(),
      style: form.style.trim() || null,
      default_title: form.default_title.trim() || null,
      color_background: form.color_background.trim() || null,
      color_border: form.color_border.trim() || null,
      color_text: form.color_text.trim() || null,
      icon: form.icon.trim() || null,
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
        description="Importez les encadres du site connecte ou creez vos propres variantes pour l'editeur."
        footer={
          <div className="flex items-center gap-3">
            {syncMessage && <span className="text-[12px] text-secondary">{syncMessage}</span>}
            <Button type="button" variant="secondary" size="sm" icon={<Import size={14} />} loading={syncing} onClick={handleSync}>
              Importer depuis le site
            </Button>
            <Button type="button" size="sm" icon={<Plus size={14} />} onClick={openCreate}>
              Creer un callout
            </Button>
          </div>
        }
      >
        {callouts.length === 0 ? (
          <div className="rounded-[14px] bg-[#f9f9fb] px-4 py-5 text-[13px] text-secondary">
            Aucun callout configure pour ce projet. Importez-les depuis le site connecte ou creez un template manuel.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {callouts.map((callout) => (
              <div key={callout.id} className="rounded-[16px] border border-border bg-[#f9f9fb] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[14px] font-semibold text-primary">{callout.label}</p>
                    <p className="mt-0.5 text-[12px] text-secondary">
                      Style {callout.style ?? '—'} · {callout.source === 'imported' ? 'Importe' : 'Manuel'}
                    </p>
                    {callout.default_title && (
                      <p className="mt-1 text-[12px] text-tertiary">Titre par defaut : {callout.default_title}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button type="button" onClick={() => openEdit(callout)} className="rounded-[8px] p-2 text-secondary hover:bg-white hover:text-primary">
                      <Pencil size={13} />
                    </button>
                    <button type="button" onClick={() => setDeleteTarget(callout)} className="rounded-[8px] p-2 text-secondary hover:bg-danger/10 hover:text-danger">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
                <div
                  className="mt-3 rounded-[12px] border px-3 py-2"
                  style={{
                    backgroundColor: callout.color_background ?? '#eff6ff',
                    borderColor: callout.color_border ?? '#3b82f6',
                    color: callout.color_text ?? '#1e3a8a',
                  }}
                >
                  <p className="text-[12px] font-semibold">{callout.default_title || callout.label}</p>
                  <p className="mt-1 text-[12px] opacity-85">Exemple de rendu du template dans l'editeur.</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </FormCard>

      <Modal
        open={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title={editing ? 'Modifier le callout' : 'Creer un callout'}
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <p className="text-[13px] text-secondary">
            Configurez le template qui sera reutilisable dans l'editeur.
          </p>
          <Input label="Nom" value={form.label} onChange={setField('label')} required />
          <Input label="Type / style" value={form.style} onChange={setField('style')} placeholder="info" />
          <Input label="Titre par defaut" value={form.default_title} onChange={setField('default_title')} placeholder="A retenir" />
          <Input label="Couleur de fond" value={form.color_background} onChange={setField('color_background')} placeholder="#eff6ff" />
          <Input label="Couleur de bordure" value={form.color_border} onChange={setField('color_border')} placeholder="#3b82f6" />
          <Input label="Couleur du texte" value={form.color_text} onChange={setField('color_text')} placeholder="#1e3a8a" />
          <Input label="Icone" value={form.icon} onChange={setField('icon')} placeholder="info" />
          {formError && <p className="text-[12px] text-danger">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setModalOpen(false)}>Annuler</Button>
            <Button type="submit" loading={saving}>{editing ? 'Mettre a jour' : 'Creer'}</Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={Boolean(deleteTarget)}
        onClose={() => !deleting && setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Supprimer ce callout ?"
        description="Le template sera retire du projet s'il n'est pas deja utilise dans un article."
        confirmLabel="Supprimer"
        loading={deleting}
        variant="danger"
      />
    </div>
  )
}
