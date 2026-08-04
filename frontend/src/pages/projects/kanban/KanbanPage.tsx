import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CalendarClock, ExternalLink, FileText, Loader2, Plus, RefreshCw } from '@/components/ui/hugeIcons'
import {
  listArticles, createArticle, publishArticle, unpublishArticle, markReadyArticle, archiveArticle,
  scheduleArticle,
} from '@/api/articles'
import { listCategories } from '@/api/categories'
import type { Article, Category } from '@/types'
import { ArticleStatus, articleStatusLabel, type ArticleStatusCode } from '@/lib/status'
import { formatDate } from '@/utils/format'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import ArticleScoreBadges from '@/components/ui/ArticleScoreBadges'

type ColumnDef = {
  status: string
  label: string
  color: string
}

const COLUMNS: ColumnDef[] = [
  { status: String(ArticleStatus.OUTLINE_READY),       label: 'Brief à préparer', color: 'var(--color-accent)' },
  { status: String(ArticleStatus.WRITING_REQUESTED),   label: 'Brief prêt',       color: 'var(--color-accent)' },
  { status: String(ArticleStatus.DRAFT_READY),         label: 'Brouillon IA',     color: 'var(--color-secondary)' },
  { status: String(ArticleStatus.WRITING_IN_PROGRESS), label: 'En rédaction',     color: 'var(--color-secondary)' },
  { status: String(ArticleStatus.REVIEW_NEEDED),       label: 'En relecture',     color: 'var(--color-warning)' },
  { status: String(ArticleStatus.CORRECTION_NEEDED),   label: 'SEO à corriger',   color: 'var(--color-danger)' },
  { status: String(ArticleStatus.READY_TO_PUBLISH),    label: 'Prêt validation',  color: 'var(--color-success)' },
  { status: String(ArticleStatus.FAILED),              label: 'Échecs',           color: 'var(--color-danger)' },
]

const QUICK_ACTIONS: Partial<Record<ArticleStatusCode, { key: string; label: string }[]>> = {
  [ArticleStatus.DRAFT_READY]:       [{ key: 'mark-ready', label: 'Marquer prêt' }],
  [ArticleStatus.REVIEW_NEEDED]:     [{ key: 'mark-ready', label: 'Marquer prêt' }],
  [ArticleStatus.CORRECTION_NEEDED]: [{ key: 'mark-ready', label: 'Marquer prêt' }],
  [ArticleStatus.READY_TO_PUBLISH]:  [{ key: 'validation', label: 'Valider' }],
}

const FINAL_STATUSES = new Set<ArticleStatusCode>([
  ArticleStatus.SCHEDULED, ArticleStatus.PUBLISHED, ArticleStatus.UNPUBLISHED, ArticleStatus.ARCHIVED,
])

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function getWordCount(article: Article): number | null {
  if (article.word_count > 0) return article.word_count
  if (article.content?.trim()) {
    const words = stripHtml(article.content).split(/\s+/).filter(Boolean)
    return words.length > 0 ? words.length : null
  }
  return null
}

function formatWordCount(value: number): string {
  return `${value.toLocaleString('fr-FR')} mots`
}

function getUsefulDate(article: Article): { label: string; value: string } {
  if (article.published_at) return { label: 'Publié', value: article.published_at }
  if (article.scheduled_for) return { label: 'Planifié', value: article.scheduled_for }
  if (article.updated_at) return { label: 'Maj', value: article.updated_at }
  return { label: 'Créé', value: article.created_at }
}

function CardContent({
  article,
  categories,
  onEdit,
  onAction,
}: {
  article: Article
  categories: Category[]
  onEdit: () => void
  onAction: (key: string, article: Article) => void
}) {
  const quickActions = QUICK_ACTIONS[article.status] ?? []
  const category = categories.find((c) => c.id === article.category_id)
  const wordCount = getWordCount(article)
  const usefulDate = getUsefulDate(article)
  return (
    <div className="rounded-[16px] bg-surface p-3 hover:bg-white transition-colors">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p
          className="text-[12px] font-medium text-primary leading-snug cursor-pointer hover:text-accent transition-colors line-clamp-2 flex-1"
          onClick={onEdit}
        >
          {article.title}
        </p>
        <button
          onClick={onEdit}
          className="shrink-0 flex h-5 w-5 items-center justify-center rounded-[6px] text-tertiary hover:bg-surface-muted hover:text-primary transition-colors mt-0.5"
        >
          <ExternalLink size={10} />
        </button>
      </div>

      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-medium text-accent/80">
            {category?.name ?? 'Sans catégorie'}
          </p>
          {article.keyword && (
            <p className="mt-0.5 truncate text-[10px] text-tertiary">{article.keyword}</p>
          )}
        </div>
        <StatusBadge status={article.status} className="shrink-0" />
      </div>

      <div className="mb-2">
        <ArticleScoreBadges article={article} compact />
      </div>

      {article.is_validable === false && article.validation_reasons.length > 0 && (
        <p className="mb-2 rounded-[8px] bg-danger/5 px-2 py-1 text-[10px] text-danger" title={article.validation_reasons.join('\n')}>
          {article.validation_reasons.length} blocage{article.validation_reasons.length > 1 ? 's' : ''} de validation
        </p>
      )}

      <div className="flex items-center justify-between gap-2 text-[10px] text-tertiary">
        {wordCount !== null ? (
          <span className="flex min-w-0 items-center gap-1">
            <FileText size={10} />
            {formatWordCount(wordCount)}
          </span>
        ) : (
          <span />
        )}
        <span className="flex shrink-0 items-center gap-1">
          <CalendarClock size={10} />
          {usefulDate.label} {formatDate(usefulDate.value)}
        </span>
      </div>

      {quickActions.length > 0 && (
        <div className="flex gap-1 mt-2 pt-2 border-t border-border">
          {quickActions.map((action) => (
            <button
              key={action.key}
              onClick={(e) => { e.stopPropagation(); onAction(action.key, article) }}
              className="flex-1 rounded-[8px] bg-surface-soft px-2 py-1 text-[10px] font-medium text-secondary hover:bg-accent hover:text-white transition-colors"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function KanbanColumn({
  column,
  articles,
  categories,
  onEdit,
  onAction,
}: {
  column: ColumnDef
  articles: Article[]
  categories: Category[]
  onEdit: (a: Article) => void
  onAction: (key: string, a: Article) => void
}) {
  const columnBackground = `linear-gradient(180deg, ${column.color}1c 0%, ${column.color}0d 42%, rgba(255,255,255,0) 100%)`

  return (
    <div className="flex min-w-[220px] max-w-[220px] flex-col rounded-t-[16px] px-2 pb-2 pt-2" style={{ background: columnBackground }}>
      <div className="relative mb-3 flex items-center gap-2 rounded-t-[14px] px-1 py-2 shadow-[0_18px_26px_-26px_rgba(15,23,42,0.45)] after:absolute after:bottom-[-10px] after:left-0 after:right-0 after:h-3 after:bg-gradient-to-b after:from-black/[0.035] after:to-transparent after:content-['']">
        <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: column.color }} />
        <span className="text-[12px] font-semibold text-primary">{column.label}</span>
        <span className="text-[12px] text-tertiary bg-surface-soft rounded-full px-1.5 py-0.5">
          {articles.length}
        </span>
      </div>
      <div className="flex min-h-[90px] flex-col gap-2 rounded-b-[14px]">
        {articles.length === 0 ? (
          <div className="flex items-center justify-center rounded-[12px] border border-dashed border-border h-20">
            <p className="text-[12px] text-tertiary">Vide</p>
          </div>
        ) : (
          articles.map((article) => (
            <CardContent
              key={article.id}
              article={article}
              categories={categories}
              onEdit={() => onEdit(article)}
              onAction={onAction}
            />
          ))
        )}
      </div>
    </div>
  )
}

export default function KanbanPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [actionError, setActionError] = useState('')
  const [loadingAction, setLoadingAction] = useState(false)
  const [tick, setTick] = useState(0)

  // Create article modal state
  const [createOpen, setCreateOpen] = useState(false)
  const [createTitle, setCreateTitle] = useState('')
  const [createKeyword, setCreateKeyword] = useState('')
  const [createCategoryId, setCreateCategoryId] = useState('')
  const [creating, setCreating] = useState(false)

  // Schedule modal state
  const [scheduleTarget, setScheduleTarget] = useState<Article | null>(null)
  const [scheduleDate, setScheduleDate] = useState('')
  const [scheduling, setScheduling] = useState(false)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    listArticles(projectId, { limit: 500 })
      .then((data) => {
        if (!cancelled) {
          setArticles(data.filter((article) => !FINAL_STATUSES.has(article.status)))
          setLoadStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  async function handleAction(key: string, article: Article) {
    if (!projectId) return
    if (key === 'schedule') {
      setScheduleTarget(article)
      setScheduleDate('')
      return
    }
    setLoadingAction(true)
    setActionError('')
    try {
      let updated: Article | undefined
      if (key === 'publish') updated = await publishArticle(projectId, article.id)
      else if (key === 'unpublish') updated = await unpublishArticle(projectId, article.id)
      else if (key === 'mark-ready') updated = await markReadyArticle(projectId, article.id)
      else if (key === 'archive') updated = await archiveArticle(projectId, article.id)
      else if (key === 'validation') { navigate(`/projects/${projectId}/validation`); return }
      if (updated) {
        setArticles((prev) => prev.map((a) => a.id === updated!.id ? updated! : a))
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erreur lors de l'action.")
    } finally {
      setLoadingAction(false)
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

  function handleAddArticle() {
    setCreateOpen(true)
    setCreateTitle('')
    setCreateKeyword('')
    setCreateCategoryId('')
  }

  async function handleCreateArticle(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId || !createTitle.trim()) return
    setCreating(true)
    try {
      await createArticle(projectId, {
        title: createTitle.trim(),
        keyword: createKeyword.trim() || undefined,
        category_id: createCategoryId || undefined,
      })
      setCreateOpen(false)
      navigate(`/projects/${projectId}/ideas`)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erreur lors de la création.")
    } finally {
      setCreating(false)
    }
  }

  const knownStatuses = new Set(COLUMNS.map((column) => column.status))
  const unknownColumns: ColumnDef[] = Array.from(new Set(
    articles
      .map((article) => String(article.status))
      .filter((status) => !knownStatuses.has(status))
  )).map((status) => ({
    status,
    label: articleStatusLabel(Number(status)),
    color: 'var(--color-tertiary)',
  }))
  const allColumns = [...COLUMNS, ...unknownColumns]

  const articlesByStatus = (status: string) =>
    articles
      .filter((a) => String(a.status) === status)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error') return <ErrorState onRetry={() => setTick((t) => t + 1)} />

  return (
    <>
      <div className="flex min-h-full flex-col p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Production éditoriale</h1>
            <p className="mt-0.5 text-[14px] text-secondary">
              Contenus en fabrication. Les articles validés, programmés ou publiés sont dans Articles.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {loadingAction && <Loader2 size={14} className="animate-spin text-tertiary" />}
            <Button size="sm" icon={<Plus size={13} />} onClick={handleAddArticle}>
              Nouvel article
            </Button>
            <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick((t) => t + 1)}>
              Rafraîchir
            </Button>
          </div>
        </div>

        {actionError && (
          <div className="mb-3 shrink-0 rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[14px] text-danger flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="ml-3 text-danger/60 hover:text-danger">✕</button>
          </div>
        )}

        {/* Kanban board (lecture seule) */}
        <div className="flex gap-4 overflow-x-auto pb-4">
          {allColumns.map((col) => (
            <KanbanColumn
              key={col.status}
              column={col}
              articles={articlesByStatus(col.status)}
              categories={categories}
              onEdit={(a) => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
              onAction={handleAction}
            />
          ))}
        </div>
      </div>

      {/* Create article modal */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Ajouter un article"
        size="sm"
      >
        <form onSubmit={handleCreateArticle} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Titre *</label>
            <input
              value={createTitle}
              onChange={(e) => setCreateTitle(e.target.value)}
              placeholder="Titre de l'article"
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[14px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Mot-clé</label>
            <input
              value={createKeyword}
              onChange={(e) => setCreateKeyword(e.target.value)}
              placeholder="Mot-clé principal (optionnel)"
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[14px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Catégorie</label>
            <select
              value={createCategoryId}
              onChange={(e) => setCreateCategoryId(e.target.value)}
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[14px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            >
              <option value="">Sans catégorie</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={creating} className="flex-1 justify-center" disabled={!createTitle.trim()}>
              Créer
            </Button>
          </div>
        </form>
      </Modal>

      {/* Schedule modal */}
      <Modal
        open={!!scheduleTarget}
        onClose={() => { setScheduleTarget(null); setScheduleDate('') }}
        title="Programmer la publication"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <p className="text-[14px] text-secondary truncate">{scheduleTarget?.title}</p>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Date et heure de publication</label>
            <input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[14px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setScheduleTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" loading={scheduling} className="flex-1 justify-center" onClick={handleScheduleConfirm}>
              Programmer
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}
