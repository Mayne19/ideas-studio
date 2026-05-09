import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus, Pencil, Trash2, FolderOpen, RefreshCw, Info } from 'lucide-react'
import { listCategories, createCategory, updateCategory, deleteCategory } from '@/api/categories'
import type { CreateCategoryPayload, UpdateCategoryPayload } from '@/api/categories'
import type { Category } from '@/types'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import ConfirmModal from '@/components/ui/ConfirmModal'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'

function CategoryRow({
  category,
  onEdit,
  onDelete,
}: {
  category: Category
  onEdit: (c: Category) => void
  onDelete: (c: Category) => void
}) {
  return (
    <div className="flex items-center gap-3 rounded-[14px] bg-[#f9f9fb] px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-primary truncate">{category.name}</p>
        {category.description && (
          <p className="text-[12px] text-tertiary truncate mt-0.5">{category.description}</p>
        )}
      </div>
      <div className="flex items-center gap-3 text-[12px] text-tertiary shrink-0">
        {category.target_frequency !== null && (
          <span>{category.target_frequency} art./mois</span>
        )}
        <span>Priorité {category.priority}</span>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onEdit(category)}
          className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-[#e5e5e7] hover:text-primary transition-colors"
          title="Modifier"
        >
          <Pencil size={13} />
        </button>
        <button
          onClick={() => onDelete(category)}
          className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
          title="Supprimer"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}

type FormState = {
  name: string
  description: string
  priority: string
  target_frequency: string
}

const EMPTY_FORM: FormState = { name: '', description: '', priority: '0', target_frequency: '' }

export default function CategoriesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [categories, setCategories] = useState<Category[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Category | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null)
  const [deleting, setDeleting] = useState(false)

  function load() {
    if (!projectId) return
    listCategories(projectId)
      .then((data) => { setCategories(data); setStatus('success') })
      .catch(() => setStatus('error'))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load() }, [projectId])

  function openCreate() {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setFormError('')
    setModalOpen(true)
  }

  function openEdit(c: Category) {
    setEditTarget(c)
    setForm({
      name: c.name,
      description: c.description ?? '',
      priority: String(c.priority),
      target_frequency: c.target_frequency !== null ? String(c.target_frequency) : '',
    })
    setFormError('')
    setModalOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !form.name.trim()) return
    setFormError('')
    setSaving(true)
    try {
      const freq = form.target_frequency.trim() ? parseInt(form.target_frequency) : null
      if (editTarget) {
        const payload: UpdateCategoryPayload = {
          name: form.name.trim(),
          description: form.description.trim() || null,
          priority: parseInt(form.priority) || 0,
          target_frequency: freq,
        }
        await updateCategory(projectId, editTarget.id, payload)
      } else {
        const payload: CreateCategoryPayload = {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          priority: parseInt(form.priority) || 0,
          target_frequency: freq ?? undefined,
        }
        await createCategory(projectId, payload)
      }
      setModalOpen(false)
      load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!projectId || !deleteTarget) return
    setDeleting(true)
    try {
      await deleteCategory(projectId, deleteTarget.id)
      setDeleteTarget(null)
      load()
    } catch (err) {
      console.error(err)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Catégories</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              Organisez vos articles par thématique.
            </p>
          </div>
          <Button icon={<Plus size={14} />} size="sm" onClick={openCreate}>
            Nouvelle catégorie
          </Button>
        </div>

        {/* Sync from site — coming soon block */}
        <div className="mb-5 flex items-start gap-3 rounded-[14px] border border-border bg-[#f9f9fb] px-4 py-3">
          <Info size={15} className="mt-0.5 shrink-0 text-tertiary" />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-primary">Synchronisation depuis votre site</p>
            <p className="mt-0.5 text-[12px] text-secondary">
              Quand votre site sera connecté, Ideas Studio pourra importer automatiquement les catégories et contenus déjà publiés.
            </p>
          </div>
          <button
            disabled
            className="shrink-0 flex items-center gap-1.5 rounded-[8px] border border-border bg-surface px-3 py-1.5 text-[12px] font-medium text-tertiary opacity-50 cursor-not-allowed"
            title="Disponible quand votre site est connecté"
          >
            <RefreshCw size={12} />
            Synchroniser
          </button>
        </div>

        {status === 'loading' && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-[14px]" />
            ))}
          </div>
        )}
        {status === 'error' && (
          <ErrorState message="Impossible de charger les catégories." onRetry={load} />
        )}
        {status === 'success' && categories.length === 0 && (
          <EmptyState
            icon={<FolderOpen size={22} />}
            title="Aucune catégorie"
            description="Créez des catégories pour organiser vos articles."
            action={{ label: 'Créer une catégorie', onClick: openCreate }}
          />
        )}
        {status === 'success' && categories.length > 0 && (
          <div className="flex flex-col gap-2">
            {categories.map((c) => (
              <CategoryRow key={c.id} category={c} onEdit={openEdit} onDelete={setDeleteTarget} />
            ))}
          </div>
        )}
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editTarget ? 'Modifier la catégorie' : 'Nouvelle catégorie'}
        size="sm"
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {formError}
            </div>
          )}
          <Input
            label="Nom"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="SEO & Référencement"
            required
            autoFocus
          />
          <Textarea
            label="Description"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Articles sur les techniques SEO..."
            rows={2}
          />
          <div className="flex gap-3">
            <Input
              label="Priorité"
              type="number"
              value={form.priority}
              onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
              placeholder="0"
            />
            <Input
              label="Fréquence cible (art./mois)"
              type="number"
              value={form.target_frequency}
              onChange={(e) => setForm((f) => ({ ...f, target_frequency: e.target.value }))}
              placeholder="4"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setModalOpen(false)}
            >
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={saving} className="flex-1 justify-center">
              {editTarget ? 'Modifier' : 'Créer'}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Supprimer cette catégorie ?"
        description={`« ${deleteTarget?.name} » sera définitivement supprimée. Les articles ne seront pas supprimés.`}
        confirmLabel="Supprimer"
        loading={deleting}
        variant="danger"
      />
    </>
  )
}
