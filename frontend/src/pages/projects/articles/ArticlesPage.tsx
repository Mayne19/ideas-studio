import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, FileText, Pencil, Calendar, Trash2, Sparkles } from 'lucide-react'
import { listArticles, createArticle, publishArticle, unpublishArticle, markReadyArticle, archiveArticle, scheduleArticle, analyzeSeoArticle, deleteArticle } from '@/api/articles'
import type { CreateArticlePayload } from '@/api/articles'
import { listCategories } from '@/api/categories'
import type { Article, ArticleStatus, Category } from '@/types'
import { STATUS_LABELS, getAvailableActions } from '@/utils/articleActions'
import { formatDate } from '@/utils/format'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import StatusBadge from '@/components/ui/StatusBadge'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'

const PAGE_SIZE = 20

const ALL_STATUSES: ArticleStatus[] = [
  'draft', 'idea_proposed', 'idea_priority', 'outline_ready',
  'writing_in_progress', 'draft_ready', 'review_needed', 'correction_needed',
  'ready_to_publish', 'scheduled', 'published', 'unpublished', 'archived', 'failed',
]

const ARTICLE_TABLE_GRID = 'lg:grid-cols-[minmax(380px,1fr)_72px_98px_86px_74px_106px_168px]'

function scoreTone(value: number | null) {
  if (value === null) return 'bg-[#f0f0f2] text-tertiary'
  return value >= 70
    ? 'bg-success/10 text-[#1a7a3a]'
    : value >= 40
    ? 'bg-warning/10 text-[#c07000]'
    : 'bg-danger/10 text-danger'
}

function ScorePill({ label, value }: { label: string; value: number | null }) {
  return (
    <span className={`inline-flex w-fit items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-medium lg:w-full ${scoreTone(value)}`}>
      {label} {value === null ? '—' : Math.round(value)}
    </span>
  )
}

function EmptyScore() {
  return <ScorePill label="" value={null} />
}

function ArticleRow({
  article,
  categories,
  onEdit,
  onAction,
}: {
  article: Article
  categories: Category[]
  onEdit: (a: Article) => void
  onAction: (key: string, a: Article) => void
}) {
  const category = categories.find((c) => c.id === article.category_id)
  const actions = getAvailableActions(article.status)

  const allActions = [
    ...actions,
    { key: 'analyze-seo', label: 'Analyser SEO', variant: 'secondary' as const },
    ...(!['published', 'archived', 'scheduled'].includes(article.status)
      ? [{ key: 'schedule', label: 'Programmer', variant: 'secondary' as const }]
      : []),
    { key: 'delete', label: 'Supprimer', variant: 'danger' as const },
  ]

  return (
    <div className={`grid gap-3 rounded-[14px] bg-[#f9f9fb] px-4 py-3 transition-colors hover:bg-[#f0f0f2] lg:items-center ${ARTICLE_TABLE_GRID}`}>
      <div className="min-w-0">
        <button
          type="button"
          className="block w-full truncate text-left text-[13px] font-medium leading-snug text-primary transition-colors hover:text-accent"
          onClick={() => onEdit(article)}
          title={article.title}
        >
          {article.title}
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-tertiary">
          <span className="font-medium text-accent/80">{category?.name ?? 'Sans catégorie'}</span>
          <span>·</span>
          <span>{formatDate(article.updated_at)}</span>
          {article.word_count > 0 && <><span>·</span><span>{article.word_count} mots</span></>}
          {article.scheduled_at && (
            <><span>·</span>
            <span className="flex items-center gap-0.5 text-accent">
              <Calendar size={10} />
              {formatDate(article.scheduled_at)}
            </span></>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {article.seo_score !== null ? <ScorePill label="SEO" value={article.seo_score} /> : <EmptyScore />}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {article.readability_score !== null ? <ScorePill label="Lisibilité" value={article.readability_score} /> : <EmptyScore />}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {article.quality_score !== null ? <ScorePill label="Qualité" value={article.quality_score} /> : <EmptyScore />}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {article.eeat_score !== null ? <ScorePill label="EEAT" value={article.eeat_score} /> : <EmptyScore />}
      </div>
      <div className="flex items-center lg:justify-start">
        <StatusBadge status={article.status} />
      </div>
      <div className="flex items-center gap-1.5 lg:justify-end">
        <button
          type="button"
          onClick={() => onEdit(article)}
          className="flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-[8px] bg-accent px-3 text-[12px] font-medium text-white transition-colors hover:bg-accent/90"
          title="Éditer"
        >
          <Pencil size={12} />
          Éditer
        </button>
        {allActions.length > 0 && (
          <select
            onChange={(e) => { if (e.target.value) { onAction(e.target.value, article); e.target.value = '' } }}
            className="h-8 w-[82px] cursor-pointer rounded-[8px] border border-border bg-surface px-1.5 text-[11px] text-secondary transition-colors hover:bg-[#e5e5e7]"
            defaultValue=""
            aria-label={`Actions pour ${article.title}`}
          >
            <option value="" disabled>Actions</option>
            {allActions.map((a) => (
              <option key={a.key} value={a.key}>{a.label}</option>
            ))}
          </select>
        )}
      </div>
    </div>
  )
}

export default function ArticlesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const [filterStatus, setFilterStatus] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const [tick, setTick] = useState(0)
  const [actionError, setActionError] = useState('')

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({ title: '', keyword: '', category_id: '' })
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)

  const [scheduleTarget, setScheduleTarget] = useState<Article | null>(null)
  const [scheduleDate, setScheduleDate] = useState('')
  const [scheduling, setScheduling] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<Article | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setStatus('loading') })
    listArticles(projectId, {
      status: filterStatus || undefined,
      category_id: filterCategory || undefined,
      search: debouncedSearch || undefined,
      skip: 0,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        if (!cancelled) {
          setArticles(data)
          setHasMore(data.length === PAGE_SIZE)
          setStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [projectId, filterStatus, filterCategory, debouncedSearch, tick])

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFilterSearch(e.target.value)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setDebouncedSearch(e.target.value), 400)
  }

  function loadMore() {
    if (!projectId) return
    setLoadingMore(true)
    listArticles(projectId, {
      status: filterStatus || undefined,
      category_id: filterCategory || undefined,
      search: debouncedSearch || undefined,
      skip: articles.length,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        setArticles((prev) => [...prev, ...data])
        setHasMore(data.length === PAGE_SIZE)
        setLoadingMore(false)
      })
      .catch(() => setLoadingMore(false))
  }

  async function handleCreate(e: React.FormEvent) {
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
      setCreateForm({ title: '', keyword: '', category_id: '' })
      navigate(`/projects/${projectId}/articles/${article.id}/edit`)
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Erreur lors de la création')
    } finally {
      setCreating(false)
    }
  }

  async function handleAction(key: string, article: Article) {
    if (!projectId) return
    if (key === 'schedule') {
      setScheduleTarget(article)
      setScheduleDate('')
      return
    }
    if (key === 'delete') {
      setDeleteTarget(article)
      return
    }
    setActionError('')
    try {
      let updated: Article | undefined
      if (key === 'publish') updated = await publishArticle(projectId, article.id)
      else if (key === 'unpublish') updated = await unpublishArticle(projectId, article.id)
      else if (key === 'mark-ready') updated = await markReadyArticle(projectId, article.id)
      else if (key === 'archive') updated = await archiveArticle(projectId, article.id)
      else if (key === 'analyze-seo') { await analyzeSeoArticle(projectId, article.id); return }
      if (updated) {
        setArticles((prev) => prev.map((a) => a.id === updated!.id ? updated! : a))
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de l\'action.')
    }
  }

  async function handleDeleteConfirm() {
    if (!projectId || !deleteTarget) return
    setDeleting(true)
    try {
      await deleteArticle(projectId, deleteTarget.id)
      setArticles((prev) => prev.filter((a) => a.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la suppression.')
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  async function handleScheduleConfirm() {
    if (!projectId || !scheduleTarget || !scheduleDate) return
    setScheduling(true)
    try {
      const updated = await scheduleArticle(projectId, scheduleTarget.id, new Date(scheduleDate).toISOString())
      setArticles((prev) => prev.map((a) => a.id === updated.id ? updated : a))
      setScheduleTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la programmation.')
    } finally {
      setScheduling(false)
    }
  }

  const statusOptions = [
    { value: '', label: 'Tous les statuts' },
    ...ALL_STATUSES.map((s) => ({ value: s, label: STATUS_LABELS[s] })),
  ]

  const categoryOptions = [
    { value: '', label: 'Toutes les catégories' },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ]

  return (
    <>
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Articles</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              Gérez et rédigez vos articles SEO.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              icon={<Sparkles size={14} />}
              size="sm"
              variant="secondary"
              onClick={() => navigate(`/projects/${projectId}/generate`)}
            >
              Générer
            </Button>
            <Button icon={<Plus size={14} />} size="sm" onClick={() => setCreateOpen(true)}>
              Créer un article
            </Button>
          </div>
        </div>

        {/* Action error banner */}
        {actionError && (
          <div className="mb-4 flex items-center justify-between rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[13px] text-danger">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="ml-3 shrink-0 text-danger/60 hover:text-danger transition-colors">✕</button>
          </div>
        )}

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Input
            placeholder="Rechercher..."
            value={filterSearch}
            onChange={handleSearchChange}
            className="w-48"
          />
          <Select
            options={statusOptions}
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-44"
          />
          {categories.length > 0 && (
            <Select
              options={categoryOptions}
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-56"
            />
          )}
        </div>

        {/* Content */}
        {status === 'loading' && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-[14px]" />
            ))}
          </div>
        )}
        {status === 'error' && (
          <ErrorState message="Impossible de charger les articles." onRetry={() => setTick((t) => t + 1)} />
        )}
        {status === 'success' && articles.length === 0 && (
          <EmptyState
            icon={<FileText size={22} />}
            title="Aucun article"
            description="Créez votre premier article pour commencer à rédiger du contenu SEO."
            action={{ label: 'Créer un article', onClick: () => setCreateOpen(true) }}
          />
        )}
        {status === 'success' && articles.length > 0 && (
          <>
            <div className={`hidden gap-3 px-4 pb-1.5 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid ${ARTICLE_TABLE_GRID}`}>
              <div>Titre / Catégorie</div>
              <div className="text-center">SEO</div>
              <div className="text-center">Lisibilité</div>
              <div className="text-center">Qualité</div>
              <div className="text-center">EEAT</div>
              <div>Statut</div>
              <div className="text-right">Actions</div>
            </div>
            <div className="flex flex-col gap-1.5">
              {articles.map((article) => (
                <ArticleRow
                  key={article.id}
                  article={article}
                  categories={categories}
                  onEdit={(a) => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                  onAction={handleAction}
                />
              ))}
            </div>
            {hasMore && (
              <div className="mt-4 flex justify-center">
                <Button variant="secondary" size="sm" loading={loadingMore} onClick={loadMore}>
                  Charger plus
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Schedule modal */}
      <Modal
        open={!!scheduleTarget}
        onClose={() => { setScheduleTarget(null); setScheduleDate('') }}
        title="Programmer la publication"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <p className="text-[13px] text-secondary truncate">
            {scheduleTarget?.title}
          </p>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Date et heure de publication</label>
            <input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setScheduleTarget(null)}
            >
              Annuler
            </Button>
            <Button
              size="sm"
              loading={scheduling}
              className="flex-1 justify-center"
              onClick={handleScheduleConfirm}
            >
              Programmer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete confirm modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Supprimer l'article"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-[12px] border border-danger/20 bg-danger/5 px-3.5 py-3">
            <Trash2 size={15} className="mt-0.5 shrink-0 text-danger" />
            <div>
              <p className="text-[13px] font-medium text-primary">Supprimer définitivement ?</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                L'article <strong>"{deleteTarget?.title}"</strong> sera supprimé définitivement. Cette action est irréversible.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setDeleteTarget(null)}
            >
              Annuler
            </Button>
            <Button
              size="sm"
              variant="danger"
              loading={deleting}
              className="flex-1 justify-center"
              onClick={handleDeleteConfirm}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create modal */}
      <Modal
        open={createOpen}
        onClose={() => { setCreateOpen(false); setCreateError('') }}
        title="Créer un article"
        size="sm"
      >
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          {createError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
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
          {categories.length > 0 && (
            <Select
              label="Catégorie"
              options={[{ value: '', label: 'Aucune catégorie' }, ...categories.map((c) => ({ value: c.id, label: c.name }))]}
              value={createForm.category_id}
              onChange={(e) => setCreateForm((f) => ({ ...f, category_id: e.target.value }))}
            />
          )}
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
    </>
  )
}
