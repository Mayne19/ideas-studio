import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, FileText, Pencil, Calendar, Trash2, Sparkles, Zap, Loader2, CheckCircle, AlertTriangle } from 'lucide-react'
import { listArticles, createArticle, publishArticle, unpublishArticle, markReadyArticle, archiveArticle, scheduleArticle, analyzeSeoArticle, deleteArticle, generateArticle } from '@/api/articles'
import type { CreateArticlePayload, GenerateArticleRequest } from '@/api/articles'
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
import ToggleSwitch from '@/components/ui/ToggleSwitch'

const PAGE_SIZE = 20

const ALL_STATUSES: ArticleStatus[] = [
  'draft', 'idea_proposed', 'idea_priority', 'outline_ready',
  'writing_in_progress', 'draft_ready', 'review_needed', 'correction_needed',
  'ready_to_publish', 'scheduled', 'published', 'unpublished', 'archived', 'failed',
]

const ARTICLE_TABLE_GRID = 'lg:grid-cols-[minmax(320px,1fr)_86px_70px_70px_70px_82px_72px_86px_150px]'

type ScoreFilter =
  | ''
  | 'global_gte_90'
  | 'global_lt_90'
  | 'seo_lt_85'
  | 'quality_lt_85'
  | 'geo_lt_80'
  | 'originality_lt_85'
  | 'critical'

function finiteScore(value: unknown): number | null {
  if (typeof value !== 'number') return null
  return Number.isFinite(value) ? value : null
}

function scoreTone(value: number | null, valid?: boolean | null) {
  if (value === null) return 'bg-[#f0f0f2] text-tertiary'
  if (valid === false) return 'bg-warning/10 text-[#9B6B19]'
  return value >= 70
    ? 'bg-success/10 text-[#1a7a3a]'
    : value >= 40
    ? 'bg-warning/10 text-[#c07000]'
    : 'bg-danger/10 text-danger'
}

function ScorePill({ label, value, valid }: { label: string; value: number | null; valid?: boolean | null }) {
  return (
    <span className={`inline-flex w-fit items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-medium lg:w-full ${scoreTone(value, valid)}`}>
      {label} {value === null ? '—' : valid === false ? `${Math.round(value)} incomplet` : Math.round(value)}
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
  const geoScore = article.geo_optimization_json ? finiteScore((article.geo_optimization_json as Record<string, unknown>).geo_score ?? (article.geo_optimization_json as Record<string, unknown>).score) : null
  const originalityScore = article.originality_report_json ? finiteScore((article.originality_report_json as Record<string, unknown>).heuristic_score) : null
  const estCost = article.estimated_cost_json ? finiteScore((article.estimated_cost_json as Record<string, unknown>).estimated_cost_eur) : null

  const allActions = [
    ...actions,
    { key: 'analyze-seo', label: 'Analyser SEO', variant: 'secondary' as const },
    ...(!['published', 'archived', 'scheduled'].includes(article.status)
      ? [{ key: 'schedule', label: 'Programmer', variant: 'secondary' as const }]
      : []),
    { key: 'delete', label: 'Supprimer', variant: 'danger' as const },
  ]

  return (
    <div className={`grid gap-3 rounded-[14px] border border-border bg-surface px-4 py-3 transition-colors hover:bg-surface-soft lg:items-center ${ARTICLE_TABLE_GRID}`}>
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
          {article.is_validable === false && article.validation_reasons.length > 0 && (
            <span className="flex items-center gap-0.5 text-danger" title={article.validation_reasons.join('\n')}>
              <AlertTriangle size={10} />
              {article.validation_reasons.length} blocage{article.validation_reasons.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        <ScorePill label="Global" value={finiteScore(article.global_score)} valid={article.global_score_valid} />
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {article.seo_score !== null ? <ScorePill label="SEO" value={finiteScore(article.seo_score)} /> : <EmptyScore />}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {article.quality_score !== null ? <ScorePill label="Qualité" value={finiteScore(article.quality_score)} /> : <EmptyScore />}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        <ScorePill label="GEO" value={geoScore} />
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        <ScorePill label="Orig." value={originalityScore} />
      </div>
      <div className="flex flex-wrap items-center gap-1.5 lg:block">
        {estCost !== null ? (
          <span className="inline-flex w-fit items-center justify-center rounded-full bg-[#eef2ff] px-1.5 py-0.5 text-[10px] font-medium text-[#4f46e5] lg:w-full">
            {estCost.toFixed(4)} €
          </span>
        ) : <EmptyScore />}
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
  const [filterBlockedCost, setFilterBlockedCost] = useState('')
  const [filterScore, setFilterScore] = useState<ScoreFilter>('')
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

  const [generateOpen, setGenerateOpen] = useState(false)
  const [generateForm, setGenerateForm] = useState<GenerateArticleRequest>({})
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [generateResult, setGenerateResult] = useState<{ id: string; title: string } | null>(null)

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
      blocked_cost_limit: filterBlockedCost ? Number(filterBlockedCost) : undefined,
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
  }, [projectId, filterStatus, filterCategory, debouncedSearch, filterBlockedCost, tick])

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
      blocked_cost_limit: filterBlockedCost ? Number(filterBlockedCost) : undefined,
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

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId) return
    setGenerateError('')
    setGenerateResult(null)
    setGenerating(true)
    try {
      const res = await generateArticle(projectId, generateForm)
      setGenerateResult({ id: res.id, title: res.title })
      setTick((t) => t + 1)
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : 'Erreur lors de la génération')
    } finally {
      setGenerating(false)
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

  const scoreOptions = [
    { value: '', label: 'Tous les scores' },
    { value: 'global_gte_90', label: 'Global ≥ 90' },
    { value: 'global_lt_90', label: 'Global < 90 ou incomplet' },
    { value: 'seo_lt_85', label: 'SEO < 85' },
    { value: 'quality_lt_85', label: 'Qualité < 85' },
    { value: 'geo_lt_80', label: 'GEO < 80' },
    { value: 'originality_lt_85', label: 'Originalité < 85' },
    { value: 'critical', label: 'Warnings critiques' },
  ]

  function matchesScoreFilter(article: Article) {
    const global = finiteScore(article.global_score)
    const seo = finiteScore(article.seo_score)
    const quality = finiteScore(article.quality_score)
    const geo = article.geo_optimization_json ? finiteScore((article.geo_optimization_json as Record<string, unknown>).geo_score ?? (article.geo_optimization_json as Record<string, unknown>).score) : null
    const originality = article.originality_report_json ? finiteScore((article.originality_report_json as Record<string, unknown>).heuristic_score) : null
    if (filterScore === 'global_gte_90') return global !== null && global >= 90 && article.global_score_valid !== false
    if (filterScore === 'global_lt_90') return global === null || global < 90 || article.global_score_valid === false
    if (filterScore === 'seo_lt_85') return seo === null || seo < 85
    if (filterScore === 'quality_lt_85') return quality === null || quality < 85
    if (filterScore === 'geo_lt_80') return geo === null || geo < 80
    if (filterScore === 'originality_lt_85') return originality === null || originality < 85
    if (filterScore === 'critical') return article.critical_warnings.length > 0
    return true
  }

  const visibleArticles = articles.filter(matchesScoreFilter)

  return (
    <>
      <div className="project-page project-page--wide">
        {/* Header */}
        <div className="project-page-header">
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
              onClick={() => { setGenerateOpen(true); setGenerateForm({}); setGenerateError(''); setGenerateResult(null) }}
            >
              Générer un article
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
        <div className="mb-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-[minmax(220px,1.25fr)_220px_190px_220px_140px_auto]">
          <Input
            placeholder="Rechercher..."
            value={filterSearch}
            onChange={handleSearchChange}
            className="w-full"
          />
          <Select
            options={scoreOptions}
            value={filterScore}
            onChange={(e) => setFilterScore(e.target.value as ScoreFilter)}
            className="w-full"
          />
          <Select
            options={statusOptions}
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-full"
          />
          {categories.length > 0 && (
            <Select
              options={categoryOptions}
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-full"
            />
          )}
          <Input
            placeholder="Coût max (€)"
            type="number"
            min="0"
            step="0.0001"
            value={filterBlockedCost}
            onChange={(e) => setFilterBlockedCost(e.target.value)}
            className="w-full"
            title="Filtrer les articles dont le coût estimé dépasse ce montant"
          />
          <Button size="sm" variant="secondary" className="justify-center" onClick={() => navigate(`/projects/${projectId}/validation`)}>
            Validation
          </Button>
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
        {status === 'success' && visibleArticles.length === 0 && (
          <EmptyState
            icon={<FileText size={22} />}
            title="Aucun article"
            description="Créez votre premier article pour commencer à rédiger du contenu SEO."
            action={{ label: 'Créer un article', onClick: () => setCreateOpen(true) }}
          />
        )}
        {status === 'success' && visibleArticles.length > 0 && (
          <>
            <div className={`hidden gap-3 px-4 pb-1.5 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid ${ARTICLE_TABLE_GRID}`}>
              <div>Titre / Catégorie</div>
              <div className="text-center">Global</div>
              <div className="text-center">SEO</div>
              <div className="text-center">Qualité</div>
              <div className="text-center">GEO</div>
              <div className="text-center">Orig.</div>
              <div className="text-center">Coût</div>
              <div>Statut</div>
              <div className="text-right">Actions</div>
            </div>
            <div className="flex flex-col gap-1.5">
              {visibleArticles.map((article) => (
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

      {/* Generate article modal */}
      <Modal
        open={generateOpen}
        onClose={() => { setGenerateOpen(false); setGenerateForm({}); setGenerateError(''); setGenerateResult(null) }}
        title="Générer un article complet"
        size="md"
      >
        {generateResult ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-start gap-3 rounded-[12px] border border-success/20 bg-success/5 px-3.5 py-3">
              <CheckCircle size={15} className="mt-0.5 shrink-0 text-[#1a7a3a]" />
              <div>
                <p className="text-[13px] font-medium text-primary">{generateResult.title}</p>
                <p className="mt-0.5 text-[12px] text-secondary">Article généré avec succès</p>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                variant="secondary"
                size="sm"
                className="flex-1 justify-center"
                onClick={() => { setGenerateOpen(false); setGenerateResult(null); setGenerateForm({}) }}
              >
                Fermer
              </Button>
              <Button
                size="sm"
                className="flex-1 justify-center"
                onClick={() => { navigate(`/projects/${projectId}/articles/${generateResult.id}/edit`); setGenerateOpen(false) }}
              >
                Ouvrir dans l'éditeur
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleGenerate} className="flex flex-col gap-4">
            {generateError && (
              <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
                {generateError}
              </div>
            )}
            <Input
              label="Titre souhaité"
              value={generateForm.preferred_title ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, preferred_title: e.target.value || null }))}
              placeholder="Comment optimiser son SEO en 2025"
              hint="Laissez vide pour que l'IA propose un titre"
            />
            <Input
              label="Mot-clé principal"
              value={generateForm.keyword ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, keyword: e.target.value || null }))}
              placeholder="optimisation seo"
            />
            {categories.length > 0 && (
              <Select
                label="Catégorie"
                options={[{ value: '', label: 'Aucune catégorie' }, ...categories.map((c) => ({ value: c.id, label: c.name }))]}
                value={generateForm.category_id ?? ''}
                onChange={(e) => setGenerateForm((f) => ({ ...f, category_id: e.target.value || null }))}
              />
            )}
            <Input
              label="Audience cible (optionnel)"
              value={generateForm.audience ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, audience: e.target.value || null }))}
              placeholder="Développeurs web"
            />
            <Input
              label="Angle éditorial (optionnel)"
              value={generateForm.angle ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, angle: e.target.value || null }))}
              placeholder="Guide pratique avec exemples"
            />
            <div className="flex flex-wrap items-center gap-4">
              <ToggleSwitch
                checked={generateForm.include_faq ?? false}
                onChange={(checked) => setGenerateForm((f) => ({ ...f, include_faq: checked }))}
                label="Inclure FAQ"
              />
              <ToggleSwitch
                checked={generateForm.include_callouts ?? false}
                onChange={(checked) => setGenerateForm((f) => ({ ...f, include_callouts: checked }))}
                label="Inclure callouts"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="flex-1 justify-center"
                onClick={() => { setGenerateOpen(false); setGenerateForm({}); setGenerateError('') }}
              >
                Annuler
              </Button>
              <Button
                type="submit"
                size="sm"
                loading={generating}
                icon={generating ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                className="flex-1 justify-center"
              >
                Générer
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </>
  )
}
