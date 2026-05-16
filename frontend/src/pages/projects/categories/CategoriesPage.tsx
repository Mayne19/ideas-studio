import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { amber, blue, crimson, cyan, grass, indigo, orange, plum, slate, teal, tomato, violet } from '@radix-ui/colors'
import { Plus, Pencil, Trash2, FolderOpen, RefreshCw, Info, Palette, ExternalLink } from 'lucide-react'
import { listCategories, createCategory, updateCategory, deleteCategory, syncCategories } from '@/api/categories'
import type { CreateCategoryPayload, UpdateCategoryPayload } from '@/api/categories'
import { listArticles, patchArticle } from '@/api/articles'
import type { Article, Category } from '@/types'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import ConfirmModal from '@/components/ui/ConfirmModal'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'
import StatusBadge from '@/components/ui/StatusBadge'
import { formatDate } from '@/utils/format'

const RADIX_CATEGORY_COLORS = [
  { name: 'Bleu', value: blue.blue9 },
  { name: 'Indigo', value: indigo.indigo9 },
  { name: 'Violet', value: violet.violet9 },
  { name: 'Prune', value: plum.plum9 },
  { name: 'Cyan', value: cyan.cyan9 },
  { name: 'Teal', value: teal.teal9 },
  { name: 'Vert', value: grass.grass9 },
  { name: 'Ambre', value: amber.amber9 },
  { name: 'Orange', value: orange.orange9 },
  { name: 'Tomate', value: tomato.tomato9 },
  { name: 'Crimson', value: crimson.crimson9 },
  { name: 'Slate', value: slate.slate9 },
]

const CATEGORY_COLORS = RADIX_CATEGORY_COLORS.map((color) => color.value)
const DEFAULT_CATEGORY_COLOR = blue.blue9

function isValidHexColor(value: string | null | undefined): value is string {
  return typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value)
}

function fallbackColorFromName(name: string): string {
  const total = name.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return CATEGORY_COLORS[total % CATEGORY_COLORS.length] ?? DEFAULT_CATEGORY_COLOR
}

function categoryColor(category: Pick<Category, 'name' | 'color'>): string {
  return isValidHexColor(category.color) ? category.color : fallbackColorFromName(category.name)
}

function normalizeColor(value: string): string {
  return isValidHexColor(value) ? value.toLowerCase() : DEFAULT_CATEGORY_COLOR
}

function CategoryColorField({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  const selected = normalizeColor(value)
  const isManualValid = isValidHexColor(value)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <label className="text-[13px] font-medium text-primary">Couleur</label>
        <div className="flex items-center gap-2 rounded-[10px] border border-border bg-[#f9f9fb] px-2 py-1">
          <span
            className="h-4 w-4 rounded-full border border-black/10"
            style={{ backgroundColor: selected }}
            aria-hidden="true"
          />
          <span className="font-mono text-[11px] uppercase text-secondary">{selected}</span>
          <input
            type="color"
            value={selected}
            onChange={(e) => onChange(e.target.value)}
            className="h-6 w-7 cursor-pointer rounded border-0 bg-transparent p-0"
            aria-label="Choisir une couleur personnalisée"
          />
        </div>
      </div>
      <div>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.04em] text-tertiary">Palette Radix</p>
        <div className="grid grid-cols-6 gap-2">
          {RADIX_CATEGORY_COLORS.map((color) => (
            <button
              key={color.value}
              type="button"
              onClick={() => onChange(color.value)}
              className={`flex h-8 items-center justify-center rounded-[10px] border bg-white transition-all ${
                selected.toLowerCase() === color.value.toLowerCase()
                  ? 'border-primary ring-2 ring-accent/20'
                  : 'border-black/5 hover:scale-[1.03]'
              }`}
              title={color.name}
              aria-label={`Choisir ${color.name}`}
            >
              <span
                className="h-4 w-4 rounded-full border border-black/10"
                style={{ backgroundColor: color.value }}
                aria-hidden="true"
              />
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] font-medium text-secondary">Code hexadécimal</label>
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="#2563eb"
          className={`w-full rounded-[10px] bg-white px-3 py-2 font-mono text-[13px] text-primary outline-none transition-colors ${
            value && !isManualValid ? 'ring-1 ring-danger/40' : 'ring-1 ring-border focus:ring-accent/30'
          }`}
        />
        {value && !isManualValid && (
          <p className="text-[11px] text-danger">
            Utilisez un code couleur hexadécimal valide, par exemple #2563eb.
          </p>
        )}
      </div>
    </div>
  )
}

function CategoryColumn({
  category,
  articles,
  categories,
  movingArticleId,
  onEdit,
  onDelete,
  onOpenArticle,
  onChangeArticleCategory,
}: {
  category: Category
  articles: Article[]
  categories: Category[]
  movingArticleId: string | null
  onEdit: (c: Category) => void
  onDelete: (c: Category) => void
  onOpenArticle: (article: Article) => void
  onChangeArticleCategory: (article: Article, categoryId: string) => void
}) {
  const color = categoryColor(category)
  const columnBackground = `linear-gradient(180deg, ${color}20 0%, ${color}12 46%, ${color}08 100%)`
  const headerBackground = `linear-gradient(135deg, ${color}24 0%, ${color}12 100%)`

  return (
    <div className="flex min-h-[360px] min-w-[260px] max-w-[260px] flex-col rounded-[18px] p-2" style={{ background: columnBackground }}>
      <div className="flex items-start gap-3 rounded-[14px] px-3 py-3" style={{ background: headerBackground }}>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full border border-black/10"
              style={{ backgroundColor: color }}
              aria-hidden="true"
            />
            <p className="truncate text-[13px] font-medium text-primary">{category.name}</p>
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
            {category.target_frequency !== null && (
              <span>{category.target_frequency} art./mois</span>
            )}
            <span>Priorité {category.priority}</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
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
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] text-tertiary transition-colors hover:bg-[#e5e5e7] hover:text-primary"
                  title="Ouvrir l'article"
                >
                  <ExternalLink size={12} />
                </button>
              </div>
              <div className="mt-2 flex items-center justify-between gap-2">
                <StatusBadge status={article.status} />
                <select
                  value={article.category_id ?? ''}
                  disabled={movingArticleId === article.id}
                  onChange={(event) => onChangeArticleCategory(article, event.target.value)}
                    className="h-7 min-w-0 max-w-[150px] rounded-[8px] bg-[#f5f5f7] px-2 text-[11px] text-secondary outline-none focus:ring-1 focus:ring-accent/20 disabled:opacity-50"
                  aria-label="Changer de catégorie"
                >
                  <option value="" disabled>Sans catégorie</option>
                  {categories.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function UncategorizedColumn({
  articles,
  categories,
  movingArticleId,
  onOpenArticle,
  onChangeArticleCategory,
}: {
  articles: Article[]
  categories: Category[]
  movingArticleId: string | null
  onOpenArticle: (article: Article) => void
  onChangeArticleCategory: (article: Article, categoryId: string) => void
}) {
  return (
    <div className="flex min-h-[360px] min-w-[260px] max-w-[260px] flex-col rounded-[18px] bg-gradient-to-b from-[#f0f0f2] to-[#f7f7f9] p-2">
      <div className="rounded-[14px] bg-white/75 px-3 py-3">
        <p className="text-[13px] font-medium text-primary">Sans catégorie</p>
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
              <div className="mt-2 flex items-center justify-between gap-2">
                <StatusBadge status={article.status} />
                <select
                  value=""
                  disabled={movingArticleId === article.id}
                  onChange={(event) => onChangeArticleCategory(article, event.target.value)}
                  className="h-7 min-w-0 max-w-[150px] rounded-[8px] bg-[#f5f5f7] px-2 text-[11px] text-secondary outline-none focus:ring-1 focus:ring-accent/20 disabled:opacity-50"
                  aria-label="Changer de catégorie"
                >
                  <option value="" disabled>Classer dans...</option>
                  {categories.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
            </div>
          ))
        )}
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
}

const EMPTY_FORM: FormState = {
  name: '',
  description: '',
  color: DEFAULT_CATEGORY_COLOR,
  priority: '0',
  target_frequency: '',
}

export default function CategoriesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [categories, setCategories] = useState<Category[]>([])
  const [articles, setArticles] = useState<Article[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [movingArticleId, setMovingArticleId] = useState<string | null>(null)

  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Category | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')

  async function handleSync() {
    if (!projectId) return
    setSyncing(true)
    setSyncMessage('')
    try {
      const result = await syncCategories(projectId)
      setCategories(result)
      setSyncMessage(`${result.length} catégorie${result.length > 1 ? 's' : ''} synchronisée${result.length > 1 ? 's' : ''}.`)
    } catch {
      setSyncMessage('Impossible de synchroniser les catégories.')
    } finally {
      setSyncing(false)
      setTimeout(() => setSyncMessage(''), 3000)
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
      target_frequency: c.target_frequency !== null ? String(c.target_frequency) : '',
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
        }
        await updateCategory(projectId, editTarget.id, payload)
      } else {
        const payload: CreateCategoryPayload = {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          color: normalizeColor(form.color),
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

  async function handleChangeArticleCategory(article: Article, categoryId: string) {
    if (!projectId || article.category_id === categoryId) return
    setMovingArticleId(article.id)
    try {
      const updated = await patchArticle(projectId, article.id, { category_id: categoryId })
      setArticles((prev) => prev.map((item) => item.id === updated.id ? updated : item))
    } catch (err) {
      console.error(err)
    } finally {
      setMovingArticleId(null)
    }
  }

  return (
    <>
      <div className="mx-auto max-w-6xl">
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

        {/* Sync from site */}
        <div className="mb-5 flex items-start gap-3 rounded-[14px] border border-border bg-[#f9f9fb] px-4 py-3">
          <Info size={15} className="mt-0.5 shrink-0 text-tertiary" />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-primary">Synchronisation depuis votre site</p>
            <p className="mt-0.5 text-[12px] text-secondary">
              Importe les catégories existantes depuis les articles publiés. Les doublons sont évités.
            </p>
            {syncMessage && (
              <p className="mt-1 text-[12px] text-accent">{syncMessage}</p>
            )}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="shrink-0 flex items-center gap-1.5 rounded-[8px] border border-border bg-surface px-3 py-1.5 text-[12px] font-medium text-secondary hover:bg-[#f0f0f2] hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-wait"
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
              Vue colonnes par catégorie. Le changement via sélecteur est enregistré ; le déplacement drag/drop sera bientôt disponible.
            </p>
            <div className="flex gap-4 overflow-x-auto pb-3">
              {categories.map((c) => (
                <CategoryColumn
                  key={c.id}
                  category={c}
                  articles={articles.filter((article) => article.category_id === c.id)}
                  categories={categories}
                  movingArticleId={movingArticleId}
                  onEdit={openEdit}
                  onDelete={setDeleteTarget}
                  onOpenArticle={(article) => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                  onChangeArticleCategory={handleChangeArticleCategory}
                />
              ))}
              <UncategorizedColumn
                articles={articles.filter((article) => !article.category_id)}
                categories={categories}
                movingArticleId={movingArticleId}
                onOpenArticle={(article) => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                onChangeArticleCategory={handleChangeArticleCategory}
              />
            </div>
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
          <div className="rounded-[16px] bg-[#f9f9fb] p-3">
            <div className="mb-2 flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.04em] text-tertiary">
              <Palette size={13} />
              Apparence
            </div>
            <CategoryColorField
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
