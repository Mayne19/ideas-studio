import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, Pencil, Trash2, FolderOpen, RefreshCw, Info, Palette, ExternalLink } from '@/components/ui/hugeIcons'
import { listCategories, createCategory, updateCategory, deleteCategory, syncCategories } from '@/api/categories'
import type { CreateCategoryPayload, UpdateCategoryPayload } from '@/api/categories'
import { listArticles, createArticle } from '@/api/articles'
import type { CreateArticlePayload } from '@/api/articles'
import type { Article, Category } from '@/types'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import ConfirmModal from '@/components/ui/ConfirmModal'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import ToggleSwitch from '@/components/ui/ToggleSwitch'
import ColorPickerField from '@/components/ui/ColorPickerField'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'
import StatusBadge from '@/components/ui/StatusBadge'
import { DEFAULT_ACCENT_COLOR, PALETTE_COLORS, isValidHexColor, normalizeHexColor } from '@/lib/colors'
import { formatDate } from '@/utils/format'

function fallbackColorFromName(name: string): string {
  const total = name.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return PALETTE_COLORS[total % PALETTE_COLORS.length] ?? DEFAULT_ACCENT_COLOR
}

function categoryColor(category: Pick<Category, 'name' | 'color'>): string {
  return isValidHexColor(category.color) ? category.color : fallbackColorFromName(category.name)
}

function normalizeColor(value: string): string {
  return normalizeHexColor(value, DEFAULT_ACCENT_COLOR)
}

function CategoryColumn({
  category,
  articles,
  onEdit,
  onDelete,
  onOpenArticle,
  onCreateArticle,
}: {
  category: Category
  articles: Article[]
  onEdit: (c: Category) => void
  onDelete: (c: Category) => void
  onOpenArticle: (article: Article) => void
  onCreateArticle: (categoryId: string) => void
}) {
  const color = categoryColor(category)
  const columnBackground = `linear-gradient(180deg, ${color}20 0%, ${color}12 46%, ${color}08 100%)`
  const headerBackground = `linear-gradient(135deg, ${color}24 0%, ${color}12 100%)`

  return (
    <div className="flex min-h-[360px] min-w-[240px] flex-1 max-w-[360px] flex-col rounded-[18px] p-2" style={{ background: columnBackground }}>
      <div className="flex items-start gap-3 rounded-[14px] px-3 py-3" style={{ background: headerBackground }}>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full border border-black/10"
              style={{ backgroundColor: color }}
              aria-hidden="true"
            />
            <p className="truncate text-[14px] font-medium text-primary">{category.name}</p>
            <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-medium text-tertiary">
              {articles.length}
            </span>
          </div>
          {category.description && (
            <p className="text-[12px] text-tertiary truncate mt-0.5">{category.description}</p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px] text-tertiary">
            <span
              className="rounded-full px-2 py-0.5 font-medium"
              style={{
                backgroundColor: `${color}12`,
                color,
              }}
            >
              {category.color ? category.color.toUpperCase() : 'Couleur auto'}
            </span>
            {(category.monthly_frequency ?? category.target_frequency) !== null && (
              <span>{category.monthly_frequency ?? category.target_frequency} art./mois</span>
            )}
            <span>Priorité {category.priority}</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            onClick={() => onEdit(category)}
            className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-muted hover:text-primary transition-colors"
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

      <div className="mt-2 flex flex-1 flex-col gap-2">
        {articles.length === 0 ? (
          <div className="flex min-h-[140px] items-center justify-center rounded-[14px] border border-dashed border-black/5 bg-white/60 px-4 text-center">
            <p className="text-[12px] text-tertiary">Aucun article dans cette catégorie.</p>
          </div>
        ) : (
          articles.map((article) => (
            <div key={article.id} className="rounded-[14px] bg-white px-3 py-3">
              <div className="flex items-start justify-between gap-2">
                <button
                  type="button"
                  onClick={() => onOpenArticle(article)}
                  className="min-w-0 flex-1 text-left"
                >
                  <span className="block text-[12px] font-medium leading-snug text-primary [overflow-wrap:anywhere]">
                    {article.title}
                  </span>
                  <span className="mt-1 block text-[10px] text-tertiary">
                    Mis à jour le {formatDate(article.updated_at)}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => onOpenArticle(article)}
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] text-tertiary transition-colors hover:bg-surface-muted hover:text-primary"
                  title="Ouvrir l'article"
                >
                  <ExternalLink size={12} />
                </button>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <StatusBadge status={article.status} />
              </div>
            </div>
          ))
        )}
        <button
          type="button"
          onClick={() => onCreateArticle(category.id)}
          className="flex items-center justify-center gap-1.5 rounded-[12px] border border-dashed border-black/10 bg-white/50 px-3 py-2 text-[12px] font-medium text-tertiary transition-colors hover:border-accent/30 hover:text-accent hover:bg-accent/5"
        >
          <Plus size={12} />
          Créer un article
        </button>
      </div>
    </div>
  )
}

function UncategorizedColumn({
  articles,
  onOpenArticle,
  onCreateArticle,
}: {
  articles: Article[]
  onOpenArticle: (article: Article) => void
  onCreateArticle: () => void
}) {
  return (
    <div className="flex min-h-[360px] min-w-[240px] flex-1 max-w-[360px] flex-col rounded-[8px] border border-border bg-surface-soft p-2">
      <div className="rounded-[8px] border border-border bg-surface px-3 py-3">
        <p className="text-[14px] font-medium text-primary">Sans catégorie</p>
        <p className="mt-0.5 text-[12px] text-tertiary">
          {articles.length}
        </p>
      </div>
      <div className="mt-2 flex flex-1 flex-col gap-2">
        {articles.length === 0 ? (
          <div className="flex min-h-[140px] items-center justify-center rounded-[14px] border border-dashed border-black/5 bg-white/60 px-4 text-center">
            <p className="text-[12px] text-tertiary">Aucun article sans catégorie.</p>
          </div>
        ) : (
          articles.map((article) => (
            <div key={article.id} className="rounded-[14px] bg-white px-3 py-3">
              <button
                type="button"
                onClick={() => onOpenArticle(article)}
                className="block w-full text-left text-[12px] font-medium leading-snug text-primary [overflow-wrap:anywhere]"
              >
                {article.title}
              </button>
              <div className="mt-2 flex items-center gap-2">
                <StatusBadge status={article.status} />
              </div>
            </div>
          ))
        )}
        <button
          type="button"
          onClick={() => onCreateArticle()}
          className="flex items-center justify-center gap-1.5 rounded-[12px] border border-dashed border-black/10 bg-white/50 px-3 py-2 text-[12px] font-medium text-tertiary transition-colors hover:border-accent/30 hover:text-accent hover:bg-accent/5"
        >
          <Plus size={12} />
          Créer un article
        </button>
      </div>
    </div>
  )
}

type FormState = {
  name: string
  description: string
  color: string
  priority: string
  target_frequency: string
  pipeline_enabled: boolean
  target_audience: string
  editorial_goal: string
}

const EMPTY_FORM: FormState = {
  name: '',
  description: '',
  color: DEFAULT_ACCENT_COLOR,
  priority: '0',
  target_frequency: '',
  pipeline_enabled: true,
  target_audience: '',
  editorial_goal: '',
}

export default function CategoriesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [categories, setCategories] = useState<Category[]>([])
  const [articles, setArticles] = useState<Article[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Category | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({ title: '', keyword: '', category_id: '' })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  async function handleSync() {
    if (!projectId) return
    setSyncing(true)
    setSyncMessage('')
    try {
      const { categories, message } = await syncCategories(projectId)
      setCategories(categories)
      setSyncMessage(message)
    } catch (err) {
      setSyncMessage(err instanceof Error ? err.message : 'Impossible de synchroniser les catégories.')
    } finally {
      setSyncing(false)
      setTimeout(() => setSyncMessage(''), 5000)
    }
  }

  function load() {
    if (!projectId) return
    Promise.all([
      listCategories(projectId),
      listArticles(projectId, { limit: 500 }),
    ])
      .then(([categoryData, articleData]) => {
        setCategories(categoryData)
        setArticles(articleData)
        setStatus('success')
      })
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
      color: categoryColor(c),
      priority: String(c.priority),
      target_frequency: (c.monthly_frequency ?? c.target_frequency) !== null ? String(c.monthly_frequency ?? c.target_frequency) : '',
      pipeline_enabled: c.pipeline_enabled !== false,
      target_audience: c.target_audience ?? '',
      editorial_goal: c.editorial_goal ?? '',
    })
    setFormError('')
    setModalOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !form.name.trim()) return
    setFormError('')
    if (!isValidHexColor(form.color)) {
      setFormError('La couleur doit être un code hexadécimal valide, par exemple #2563eb.')
      return
    }
    setSaving(true)
    try {
      const freq = form.target_frequency.trim() ? parseInt(form.target_frequency) : null
      if (editTarget) {
        const payload: UpdateCategoryPayload = {
          name: form.name.trim(),
          description: form.description.trim() || null,
          color: normalizeColor(form.color),
          priority: parseInt(form.priority) || 0,
          target_frequency: freq,
          monthly_frequency: freq,
          pipeline_enabled: form.pipeline_enabled,
          target_audience: form.target_audience.trim() || null,
          editorial_goal: form.editorial_goal.trim() || null,
        }
        await updateCategory(projectId, editTarget.id, payload)
      } else {
        const payload: CreateCategoryPayload = {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          color: normalizeColor(form.color),
          priority: parseInt(form.priority) || 0,
          target_frequency: freq ?? undefined,
          monthly_frequency: freq ?? undefined,
          pipeline_enabled: form.pipeline_enabled,
          target_audience: form.target_audience.trim() || null,
          editorial_goal: form.editorial_goal.trim() || null,
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

  function handleCreateArticleInCategory(categoryId: string) {
    setCreateForm({ title: '', keyword: '', category_id: categoryId })
    setCreateError('')
    setCreateOpen(true)
  }

  function handleCreateArticleInUncategorized() {
    setCreateForm({ title: '', keyword: '', category_id: '' })
    setCreateError('')
    setCreateOpen(true)
  }

  async function handleCreateArticleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !createForm.title.trim()) return
    setCreateError('')
    setCreating(true)
    try {
      const payload: CreateArticlePayload = {
        title: createForm.title.trim(),
        keyword: createForm.keyword.trim() || undefined,
        category_id: createForm.category_id || undefined,
      }
      const article = await createArticle(projectId, payload)
      setCreateOpen(false)
      navigate(`/projects/${projectId}/articles/${article.id}/edit`)
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Erreur lors de la création')
    } finally {
      setCreating(false)
    }
  }

  return (
    <>
      <div className="project-page project-page--wide">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Catégories</h1>
            <p className="mt-0.5 text-[14px] text-secondary">
              Organisez vos articles par thématique.
            </p>
          </div>
          <Button icon={<Plus size={14} />} size="sm" onClick={openCreate}>
            Nouvelle catégorie
          </Button>
        </div>

        {/* Sync from site */}
        <div className="mb-5 flex items-start gap-3 rounded-[14px] border border-border bg-surface-soft px-4 py-3">
          <Info size={15} className="mt-0.5 shrink-0 text-tertiary" />
          <div className="flex-1 min-w-0">
            <p className="text-[14px] font-medium text-primary">Synchronisation depuis votre site</p>
             <p className="mt-0.5 text-[12px] text-secondary">
               Importe les catégories depuis l'API publique de votre site connecté (name, slug, couleur). Les doublons sont évités.
             </p>
            {syncMessage && (
              <p className="mt-1 text-[12px] text-accent">{syncMessage}</p>
            )}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="shrink-0 flex items-center gap-1.5 rounded-[8px] border border-border bg-surface px-3 py-1.5 text-[12px] font-medium text-secondary hover:bg-surface-soft hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-wait"
          >
            <RefreshCw size={12} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Synchronisation…' : 'Synchroniser depuis votre site'}
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
            <p className="text-[12px] text-tertiary">
              Vue colonnes par catégorie.
            </p>
            <div className="flex gap-4 overflow-x-auto pb-3">
              {categories.map((c) => (
                <CategoryColumn
                  key={c.id}
                  category={c}
                  articles={articles.filter((article) => article.category_id === c.id)}
                  onEdit={openEdit}
                  onDelete={setDeleteTarget}
                  onOpenArticle={(article) => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                  onCreateArticle={handleCreateArticleInCategory}
                />
              ))}
              <UncategorizedColumn
                articles={articles.filter((article) => !article.category_id)}
                onOpenArticle={(article) => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                onCreateArticle={handleCreateArticleInUncategorized}
              />
            </div>
          </div>
        )}
      </div>

      {/* Create article modal */}
      <Modal
        open={createOpen}
        onClose={() => { setCreateOpen(false); setCreateError('') }}
        title="Créer un article"
        size="sm"
      >
        <form onSubmit={handleCreateArticleSubmit} className="flex flex-col gap-4">
          {createError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
              {createError}
            </div>
          )}
          <Input
            label="Titre"
            value={createForm.title}
            onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Comment optimiser son SEO en 2025"
            required
            autoFocus
          />
          <Input
            label="Mot-clé principal"
            value={createForm.keyword}
            onChange={(e) => setCreateForm((f) => ({ ...f, keyword: e.target.value }))}
            placeholder="optimisation seo"
          />
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setCreateOpen(false)}
            >
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={creating} className="flex-1 justify-center">
              Créer
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editTarget ? 'Modifier la catégorie' : 'Nouvelle catégorie'}
        size="sm"
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
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
          <div className="rounded-[16px] bg-surface-soft p-3">
            <div className="mb-2 flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.04em] text-tertiary">
              <Palette size={13} />
              Apparence
            </div>
            <ColorPickerField
              value={form.color}
              onChange={(color) => setForm((f) => ({ ...f, color }))}
            />
          </div>
          <div className="flex gap-3">
            <Input
              label="Priorité"
              type="number"
              value={form.priority}
              onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
              placeholder="0"
            />
            <Input
              label="Fréquence mensuelle (art./mois)"
              type="number"
              value={form.target_frequency}
              onChange={(e) => setForm((f) => ({ ...f, target_frequency: e.target.value }))}
              placeholder="4"
            />
          </div>
          <Input
            label="Audience cible"
            value={form.target_audience}
            onChange={(e) => setForm((f) => ({ ...f, target_audience: e.target.value }))}
            placeholder="Développeurs web, freelances, entrepreneurs..."
          />
          <Textarea
            label="Objectif éditorial"
            value={form.editorial_goal}
            onChange={(e) => setForm((f) => ({ ...f, editorial_goal: e.target.value }))}
            placeholder="Éduquer sur les bonnes pratiques, générer des leads..."
            rows={2}
          />
          <div className="flex items-center justify-between rounded-[12px] bg-surface-soft px-3.5 py-3">
            <div>
              <p className="text-[14px] font-medium text-primary">Inclure dans le pipeline</p>
              <p className="mt-0.5 text-[12px] text-secondary">Génération automatique d'idées activée.</p>
            </div>
            <ToggleSwitch
              checked={form.pipeline_enabled}
              onChange={(v) => setForm((f) => ({ ...f, pipeline_enabled: v }))}
              ariaLabel="Inclure dans le pipeline automatique"
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
